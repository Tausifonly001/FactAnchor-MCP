"""Clean Crawl4AI Markdown output into a compact, readable context snippet."""

from __future__ import annotations

import re


def clean_markdown(markdown: str) -> str:
    """Normalise Crawl4AI Markdown: collapse whitespace, drop noisy blank lines."""
    if not markdown:
        return ""
    text = markdown.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*\|.*\|\s*$\n?", "", text, flags=re.MULTILINE)
    return text.strip()


def truncate(text: str, max_chars: int = 6000) -> str:
    """Truncate context to keep the prompt within model limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated]"
