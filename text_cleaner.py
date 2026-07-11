"""Clean raw web HTML/text into a compact, readable context snippet."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and collapse whitespace into clean plain text."""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return _collapse_whitespace(text)


def _collapse_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def truncate(text: str, max_chars: int = 6000) -> str:
    """Truncate context to keep the prompt within model limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated]"
