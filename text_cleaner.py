"""Clean Crawl4AI Markdown output into a compact, readable context snippet."""

from __future__ import annotations

import re


def clean_markdown(markdown: str) -> str:
    """Normalise Crawl4AI Markdown: collapse whitespace, keep tables intact."""
    if not markdown:
        return ""
    text = markdown.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_context(text: str) -> str:
    """Neutralise tags that could escape the <verified_context> fence."""
    if not text:
        return ""
    text = re.sub(r"</?\s*verified_context\s*>", "", text, flags=re.IGNORECASE)
    return text


def truncate(text: str, max_chars: int = 40000) -> str:
    """Truncate context to keep the prompt within model limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated]"
