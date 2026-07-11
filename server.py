"""FactAnchor-MCP: a zero-cost local MCP server that grounds LLM answers
in fetched, verified web text using strict guardrail prompting.

Run locally (no cloud hosting) and connect it to Claude Desktop / Cursor /
VS Code via the MCP config. See README.md for the 1-minute quick start.
"""

from __future__ import annotations

import sys

import requests
from mcp.server.fastmcp import FastMCP

import guardrail
import text_cleaner

mcp = FastMCP("FactAnchor-MCP")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


@mcp.tool()
def fetch_verified_context(query: str, max_results: int = 3) -> str:
    """Fetch real, source-of-truth web text for a topic and wrap it in a
    strict fact-anchoring guardrail so the LLM answers ONLY from it.

    Use this tool BEFORE answering any factual question. Then answer the
    user strictly from the returned <verified_context> block and follow the
    embedded STRICT RULES (never guess, cite sources in brackets, do not use
    pre-trained knowledge for missing info).

    Args:
        query: The factual topic or question to ground.
        max_results: How many web sources to pull (default 3, max 5).
    """
    count = max(1, min(int(max_results), 5))
    sources = _search(query, count)
    if not sources:
        return guardrail.build_guardrail(
            "(No verified web sources could be retrieved for this query. "
            "Treat the topic as unverified.)"
        )

    blocks: list[str] = []
    for title, url, snippet in sources:
        body = _fetch_page(url) or snippet
        if not body:
            continue
        header = f"SOURCE: {title}"
        if url:
            header += f"\nURL: {url}"
        blocks.append(f"{header}\n\n{body}")

    combined = "\n\n========\n\n".join(blocks)
    combined = text_cleaner.truncate(combined, max_chars=6000)
    return guardrail.build_guardrail(combined)


def _search(query: str, max_results: int) -> list[tuple[str, str, str]]:
    """Return (title, url, snippet) tuples from free DuckDuckGo search."""
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

    out: list[tuple[str, str, str]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out.append(
                    (r.get("title", "").strip(), r.get("href", "").strip(), r.get("body", "").strip())
                )
    except Exception as exc:  # network/rate-limit issues degrade gracefully
        return [("web search failed", "", f"(Web fetch failed: {exc})")]
    return out


def _fetch_page(url: str) -> str:
    """Fetch and clean the raw text of a single result page."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8, allow_redirects=True)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            return ""
        resp.encoding = resp.apparent_encoding or resp.encoding
        return text_cleaner.truncate(text_cleaner.clean_html(resp.text), max_chars=2500)
    except Exception:
        return ""


def main() -> None:
    """Console entry point (installed as `factanchor-mcp`)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
