"""Worker: scrape URLs with Crawl4AI and emit {url: markdown} as JSON.

Run as a SEPARATE process by server.py's _crawl so the headless browser's
event loop / stdio never touch the MCP server's stdio pipe (avoids the
cross-framework deadlock that hangs the tool over stdio transport).
"""
from __future__ import annotations

import asyncio
import json
import sys

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def _extract_markdown(result) -> str:
    for attr in ("fit_markdown", "markdown"):
        val = getattr(result, attr, None)
        if isinstance(val, str) and val.strip():
            return val
        if hasattr(val, "fit_markdown") and getattr(val, "fit_markdown", ""):
            return val.fit_markdown
        if hasattr(val, "raw_markdown") and getattr(val, "raw_markdown", ""):
            return val.raw_markdown
    return ""


async def _run(urls: list[str]) -> dict:
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, magic=True)
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        results = await crawler.arun_many(urls, config=run_cfg)

    out: dict[str, str] = {}
    for url, res in zip(urls, results):
        if getattr(res, "success", False):
            md = _extract_markdown(res)
            if md:
                out[url] = md
    return out


def main() -> None:
    urls = json.loads(sys.stdin.read())
    try:
        out = asyncio.run(_run(urls))
    except Exception:
        out = {}
    # Write UTF-8 bytes directly: the Windows console/pipe codec (cp1252)
    # cannot encode non-ASCII Markdown and would crash the worker.
    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
