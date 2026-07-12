"""Search backends: DuckDuckGo only (free, no API keys required).

All scraping is done locally via the `ddgs` Python package which
scrapes DuckDuckGo's public web interface. No paid APIs involved.
"""

from __future__ import annotations


def search(query: str, max_results: int) -> list[tuple[str, str, str]] | None:
    """Search via DuckDuckGo (free, rate-limited).

    Returns (title, url, snippet) tuples, or None on total failure.
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
