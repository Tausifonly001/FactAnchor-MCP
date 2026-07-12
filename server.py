"""FactAnchor-MCP: a zero-cost local MCP server that grounds LLM answers
in fetched, verified web text using strict guardrail prompting.

Web fetching uses Crawl4AI (LLM-optimized, async, strips navs/ads/footers)
and URL discovery uses free DuckDuckGo search. Runs locally (no cloud
hosting). Zero-config: the Playwright Chromium browser is installed
automatically on first start. See README.md for the 1-minute quick start.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading

from mcp.server.fastmcp import FastMCP

import guardrail
import text_cleaner

# Prevent the headless browser (and other child processes) from inheriting the
# stdio file descriptors. Without this, MCP over stdio deadlocks/corrupts
# because the browser holds the server's stdout pipe open.
for _fd in (0, 1, 2):
    try:
        os.set_inheritable(_fd, False)
    except OSError:
        pass

RATE_LIMIT_NOTE = (
    "[System Note: The search provider is temporarily rate-limiting requests. "
    "Please inform the user to try again in a few minutes, or use cached data.]"
)

mcp = FastMCP("FactAnchor-MCP")


def _ensure_browser_silent() -> None:
    """Install Playwright Chromium (idempotent). Never crash the server.

    Always runs; `playwright install` is a no-op when the build already
    matches, so this is safe to call on every startup and guarantees the
    exact Chromium build Crawl4AI expects is present.
    """
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

    Uses free DuckDuckGo search to discover URLs, then Crawl4AI to scrape
    them into clean LLM-optimized Markdown. Answer the user strictly from
    the returned <verified_context> block and follow the embedded STRICT
    RULES (never guess, cite sources in brackets, do not use pre-trained
    knowledge for missing info).

    Args:
        query: The factual topic or question to ground.
        max_results: How many web sources to pull (default 3, max 5).
    """
    try:
        count = max(1, min(int(max_results), 5))
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

    urls = [url for _title, url, _snippet in sources if url]
    try:
        texts = await asyncio.to_thread(_crawl, urls) if urls else {}
    except Exception:
        texts = {}

    blocks: list[str] = []
    for title, url, snippet in sources:
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
    combined = text_cleaner.truncate(combined, max_chars=40000)
    return guardrail.build_guardrail(combined)


def _search(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Return (title, url, snippet) tuples, or None on rate-limit/provider failure.

    Tries resilient free backends in order (duckduckgo HTML-style first when
    available, then auto / wikipedia / brave). Never raises — returns None so
    the tool can emit RATE_LIMIT_NOTE.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return [(
                "search library missing",
                "",
                "(Install a search backend: `pip install ddgs` or `pip install duckduckgo_search`)",
            )]

    # Prefer HTML-style DuckDuckGo first (most rate-limit resilient), then
    # free fallbacks. Older packages accept "html"/"lite"; newer ddgs uses
    # named engines like "duckduckgo", "auto", "wikipedia".
    backends = ("html", "lite", "duckduckgo", "auto", "wikipedia", "brave")
    last_error: Exception | None = None

    for backend in backends:
        try:
            out: list[tuple[str, str, str]] = []
            with DDGS() as ddgs:
                try:
                    results = ddgs.text(query, max_results=max_results, backend=backend)
                except TypeError:
                    results = ddgs.text(query, max_results=max_results)
                for r in results or []:
                    out.append(
                        (
                            (r.get("title") or "").strip(),
                            (r.get("href") or "").strip(),
                            (r.get("body") or "").strip(),
                        )
                    )
            if out:
                return out
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        return None
    return []


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
            [sys.executable, worker, json.dumps(urls)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
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
