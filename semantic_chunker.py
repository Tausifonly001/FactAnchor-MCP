"""Semantic chunking: extract the most relevant paragraphs using BM25.

Instead of naively truncating at N characters, this module scores each
paragraph against the query and keeps only the most relevant ones,
preserving the character budget for high-signal content.
"""

from __future__ import annotations

import math
import re


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _bm25_scores(
    query_tokens: list[str],
    paragraphs: list[list[str]],
    avg_dl: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Compute BM25 scores for each paragraph against the query."""
    # Document frequency: how many paragraphs contain each query term
    df: dict[str, int] = {}
    for para_tokens in paragraphs:
        seen = set(para_tokens)
        for qt in query_tokens:
            if qt in seen:
                df[qt] = df.get(qt, 0) + 1

    n = len(paragraphs)
    scores = []
    for para_tokens in paragraphs:
        dl = len(para_tokens)
        tf_map: dict[str, int] = {}
        for t in para_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        score = 0.0
        for qt in query_tokens:
            if qt not in tf_map:
                continue
            tf = tf_map[qt]
            doc_freq = df.get(qt, 0)
            # IDF component
            idf = math.log((n - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            # TF component with length normalization
            tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
            score += idf * tf_norm

        scores.append(score)
    return scores


def extract_relevant(
    text: str,
    query: str,
    max_chars: int = 40000,
) -> str:
    """Extract the most relevant paragraphs from text for a given query.

    Splits text into paragraphs, scores each with BM25 against the query,
    and greedily selects the highest-scoring paragraphs until the character
    budget is exhausted. Falls back to naive truncation if scoring fails.
    """
    if not text or not query:
        return text[:max_chars] if len(text) > max_chars else text

    # Split into paragraphs (double-newline separated)
    paragraphs = re.split(r"\n\s*\n", text)
    if len(paragraphs) <= 2:
        # Too few paragraphs to rerank; just truncate
        if len(text) > max_chars:
            return text[:max_chars].rstrip() + "\n...[truncated]"
        return text

    # Tokenize everything
    query_tokens = _tokenize(query)
    if not query_tokens:
        if len(text) > max_chars:
            return text[:max_chars].rstrip() + "\n...[truncated]"
        return text

    para_token_lists = [_tokenize(p) for p in paragraphs]

    # Average document length
    total_tokens = sum(len(pt) for pt in para_token_lists)
    avg_dl = total_tokens / len(para_token_lists) if para_token_lists else 1.0

    # Score paragraphs
    scores = _bm25_scores(query_tokens, para_token_lists, avg_dl)

    # Sort by score descending
    ranked = sorted(range(len(paragraphs)), key=lambda i: scores[i], reverse=True)

    # Greedily select paragraphs until budget is exhausted
    selected: list[tuple[int, str]] = []
    used_chars = 0
    for idx in ranked:
        para = paragraphs[idx]
        para_len = len(para) + 2  # +2 for the \n\n separator
        if used_chars + para_len > max_chars and selected:
            # Skip this paragraph if it would exceed budget
            continue
        selected.append((idx, para))
        used_chars += para_len
        if used_chars >= max_chars:
            break

    # Re-sort by original order to maintain readability
    selected.sort(key=lambda x: x[0])

    result = "\n\n".join(p for _, p in selected)
    if len(result) > max_chars:
        result = result[:max_chars].rstrip() + "\n...[truncated]"
    return result
