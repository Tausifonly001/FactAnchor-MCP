"""FactAnchor-MCP: a zero-cost local MCP server that grounds LLM answers
in fetched, verified web text using strict guardrail prompting.

Web fetching uses Crawl4AI (LLM-optimized, async, strips navs/ads/footers)
and URL discovery uses hybrid search (Tavily → Serper → DuckDuckGo).
Runs locally (no cloud hosting). Zero-config: the Playwright Chromium
browser is installed automatically on first start.
See README.md for the 1-minute quick start.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

import disk_cache
import guardrail
import search_backends
import semantic_chunker
import text_cleaner

# NOTE: We deliberately do NOT call os.set_inheritable(0,1,2, False) here.
# The headless browser is fully isolated in a separate worker process
# (crawl_worker.py, whose stdio is never shared with this server), so the
# MCP stdio pipe cannot be held open by the browser. Marking stdio
# non-inheritable globally would also make the pipes we create for the
# worker non-inheritable on Windows and break stdin delivery.

RATE_LIMIT_NOTE = (
    "[System Note: The search provider is temporarily rate-limiting requests. "
    "Please inform the user to try again in a few minutes, or use cached data.]"
)

# --- simple in-memory TTL cache (keyed on query + result count) ----------
_CACHE: dict[tuple, tuple[float, str]] = {}
_CACHE_TTL = 300  # seconds


def _cache_get(key: tuple) -> str | None:
    item = _CACHE.get(key)
    if item is not None and (time.time() - item[0]) < _CACHE_TTL:
        return item[1]
    _CACHE.pop(key, None)
    return None


def _cache_set(key: tuple, value: str) -> None:
    _CACHE[key] = (time.time(), value)
    if len(_CACHE) > 100:  # keep the cache bounded
        oldest = sorted(_CACHE.items(), key=lambda kv: kv[1][0])[0][0]
        _CACHE.pop(oldest, None)


def _is_safe_url(url: str) -> bool:
    """Reject non-http(s) schemes and private/loopback/metadata addresses (SSRF)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in ("localhost", "0.0.0.0", "::1") or host.endswith(".localhost"):
        return False
    if host == "169.254.169.254":  # cloud metadata endpoint
        return False
    if host.startswith("127.") or host.startswith("10."):
        return False
    if host.startswith("192.168."):
        return False
    if host.startswith("172."):  # private range 172.16.0.0/12
        try:
            second = int(host.split(".")[1])
        except (ValueError, IndexError):
            return False
        if not (16 <= second <= 31):
            return False
    return True


def _browser_already_installed() -> bool:
    """Accurately detect whether Playwright's Chromium is present.

    Uses Playwright's own API (not a loose directory scan) so we never skip
    an install when the exact required build is missing.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.isfile(path)
    except Exception:
        return False


mcp = FastMCP("FactAnchor-MCP")


def _ensure_browser_silent() -> None:
    """Install Playwright Chromium if missing. Never crash the server."""
    if _browser_already_installed():
        return
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(
                "[FactAnchor-MCP] Browser setup warning: `playwright install "
                f"chromium` exited with code {result.returncode}.\n"
            )
    except Exception as exc:
        sys.stderr.write(f"[FactAnchor-MCP] Browser setup failed: {exc}\n")


def _start_browser_setup() -> None:
    """Fire-and-forget browser install so MCP stdio startup is not blocked."""
    try:
        thread = threading.Thread(
            target=_ensure_browser_silent, daemon=True, name="factanchor-browser-setup"
        )
        thread.start()
    except Exception:
        pass


_start_browser_setup()


@mcp.tool()
async def fetch_verified_context(query: str, max_results: int = 3) -> str:
    """Fetch real, source-of-truth web text for a topic and wrap it in a
    strict fact-anchoring guardrail so the LLM answers ONLY from it.

    Uses hybrid search (Tavily → Serper → DuckDuckGo) to discover URLs,
    then Crawl4AI to scrape them into clean LLM-optimized Markdown.
    Answer the user strictly from the returned <verified_context> block
    and follow the embedded STRICT RULES (never guess, cite sources in
    brackets, do not use pre-trained knowledge for missing info).

    Args:
        query: The factual topic or question to ground.
        max_results: How many web sources to pull (default 3, max 5).
    """
    try:
        count = max(1, min(int(max_results), 5))

        # Check in-memory cache first (hot)
        cache_key = (query, count)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        # Check persistent disk cache (warm)
        cached = disk_cache.disk_get(query, count)
        if cached is not None:
            _cache_set(cache_key, cached)  # promote to in-memory
            return cached

        sources = await asyncio.to_thread(_search, query, count)
    except Exception:
        return RATE_LIMIT_NOTE

    if sources is None:
        return RATE_LIMIT_NOTE

    if not sources:
        return guardrail.build_guardrail(
            "(No verified web sources could be retrieved for this query. "
            "Treat the topic as unverified.)"
        )

    urls = [url for _title, url, _snippet in sources if url and _is_safe_url(url)]
    try:
        texts = await asyncio.to_thread(_crawl, urls) if urls else {}
    except Exception:
        texts = {}

    blocks: list[str] = []
    for title, url, snippet in sources:
        if not _is_safe_url(url):
            continue
        body = texts.get(url) or snippet
        if not body:
            continue
        header = f"SOURCE: {title}"
        if url:
            header += f"\nURL: {url}"
        blocks.append(f"{header}\n\n{body}")

    if not blocks:
        return RATE_LIMIT_NOTE

    combined = "\n\n========\n\n".join(blocks)

    # Semantic chunking: extract most relevant paragraphs for the query
    combined = await asyncio.to_thread(
        semantic_chunker.extract_relevant, combined, query, 40000
    )

    result = guardrail.build_guardrail(combined)

    # Persist to disk cache (survives restarts)
    _cache_set(cache_key, result)
    disk_cache.disk_set(query, count, result)
    return result


def _search(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Return (title, url, snippet) tuples, or None on total failure.

    Uses hybrid search: Tavily (if TAVILY_API_KEY set) → Serper (if
    SERPER_API_KEY set) → DuckDuckGo (free, rate-limited).
    """
    return search_backends.search(query, max_results)


def _crawl(urls: list[str]) -> dict[str, str]:
    """Scrape URLs concurrently with Crawl4AI into clean Markdown.

    Delegates to a SEPARATE worker process (crawl_worker.py) so the headless
    browser's event loop / stdio never touch this MCP server's stdio pipe.
    This sidesteps a cross-framework (anyio vs Playwright) deadlock that
    would otherwise hang the tool over stdio transport.

    Returns {url: cleaned_markdown}. Never raises.
    """
    import json
    import subprocess

    worker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawl_worker.py")
    try:
        proc = subprocess.run(
            [sys.executable, worker],
            input=json.dumps(urls).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )
    except Exception:
        return {}

    if not proc.stdout:
        return {}

    try:
        raw = json.loads(proc.stdout)
    except Exception:
        return {}

    out: dict[str, str] = {}
    for url, md in raw.items():
        if md:
            out[url] = text_cleaner.clean_markdown(text_cleaner.truncate(md, max_chars=10000))
    return out


def main() -> None:
    """Console entry point (installed as `factanchor-mcp`)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
