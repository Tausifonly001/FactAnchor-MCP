"""Hybrid search backends: Tavily, Serper, and DuckDuckGo.

Priority order:
1. Tavily (if TAVILY_API_KEY env var is set)
2. Serper (if SERPER_API_KEY env var is set)
3. DuckDuckGo (always available, free, rate-limited)

Each backend returns list[(title, url, snippet)] or None on failure.
"""

from __future__ import annotations

import os
import urllib.request
import json


def _search_tavily(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Search via Tavily API (https://tavily.com). Requires TAVILY_API_KEY."""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        payload = json.dumps({
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for r in data.get("results", [])[:max_results]:
            title = (r.get("title") or "").strip()
            url = (r.get("url") or "").strip()
            snippet = (r.get("content") or "").strip()
            if url:
                results.append((title, url, snippet))

        return results if results else None
    except Exception:
        return None


def _search_serper(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Search via Serper API (https://serper.dev). Requires SERPER_API_KEY."""
    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        payload = json.dumps({
            "q": query,
            "num": max_results,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": api_key,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for r in data.get("organic", [])[:max_results]:
            title = (r.get("title") or "").strip()
            url = (r.get("link") or "").strip()
            snippet = (r.get("snippet") or "").strip()
            if url:
                results.append((title, url, snippet))

        return results if results else None
    except Exception:
        return None


def _search_ddg(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Search via DuckDuckGo (free, rate-limited)."""
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


def search(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Unified search: try Tavily → Serper → DuckDuckGo.

    Returns (title, url, snippet) tuples, or None on total failure.
    """
    # 1. Tavily (paid, high quality)
    result = _search_tavily(query, max_results)
    if result is not None:
        return result

    # 2. Serper (paid, high quality)
    result = _search_serper(query, max_results)
    if result is not None:
        return result

    # 3. DuckDuckGo (free, rate-limited)
    return _search_ddg(query, max_results)
