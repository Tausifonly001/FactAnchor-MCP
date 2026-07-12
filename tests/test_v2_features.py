"""Tests for search_backends, disk_cache, and semantic_chunker."""

import os
import tempfile
import time

import disk_cache
import search_backends
import semantic_chunker


# --- search_backends tests ---

def test_search_ddg_returns_results():
    """DuckDuckGo search should return at least one result for a common query."""
    results = search_backends._search_ddg("Python programming language", 2)
    assert results is not None
    assert len(results) >= 1
    for title, url, snippet in results:
        assert isinstance(title, str)
        assert isinstance(url, str)
        assert isinstance(snippet, str)


def test_search_tavily_without_key_returns_none():
    """Tavily should return None when no API key is set."""
    old = os.environ.pop("TAVILY_API_KEY", None)
    try:
        assert search_backends._search_tavily("test", 1) is None
    finally:
        if old is not None:
            os.environ["TAVILY_API_KEY"] = old


def test_search_serper_without_key_returns_none():
    """Serper should return None when no API key is set."""
    old = os.environ.pop("SERPER_API_KEY", None)
    try:
        assert search_backends._search_serper("test", 1) is None
    finally:
        if old is not None:
            os.environ["SERPER_API_KEY"] = old


def test_unified_search_falls_back_to_ddg():
    """Unified search should fall through to DDG when no API keys are set."""
    old_t = os.environ.pop("TAVILY_API_KEY", None)
    old_s = os.environ.pop("SERPER_API_KEY", None)
    try:
        results = search_backends.search("Python programming language", 2)
        assert results is not None
        assert len(results) >= 1
    finally:
        if old_t is not None:
            os.environ["TAVILY_API_KEY"] = old_t
        if old_s is not None:
            os.environ["SERPER_API_KEY"] = old_s


# --- disk_cache tests ---

def test_disk_cache_set_and_get():
    """Disk cache should persist and retrieve values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = disk_cache.DiskCache(cache_dir=tmpdir, ttl=3600)
        cache.set("test query||3", "cached result 123")
        assert cache.get("test query||3") == "cached result 123"
        cache.close()


def test_disk_cache_expired_returns_none():
    """Expired cache entries should return None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = disk_cache.DiskCache(cache_dir=tmpdir, ttl=1)
        cache.set("expired||1", "old value")
        time.sleep(1.1)
        assert cache.get("expired||1") is None
        cache.close()


def test_disk_cache_miss_returns_none():
    """Non-existent keys should return None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = disk_cache.DiskCache(cache_dir=tmpdir, ttl=3600)
        assert cache.get("nonexistent||1") is None
        cache.close()


# --- semantic_chunker tests ---

def test_extract_relevant_basic():
    """Should extract paragraphs and not exceed max_chars."""
    text = (
        "Paris is the capital of France.\n\n"
        "Berlin is the capital of Germany.\n\n"
        "Tokyo is the capital of Japan.\n\n"
        "Paris has a population of over 2 million."
    )
    result = semantic_chunker.extract_relevant(text, "capital of France", max_chars=200)
    assert len(result) <= 200
    assert "Paris" in result


def test_extract_relevant_empty():
    """Empty text should return empty."""
    assert semantic_chunker.extract_relevant("", "query", 100) == ""


def test_extract_relevant_short_text_unchanged():
    """Short text should be returned as-is."""
    text = "Short paragraph about AI."
    result = semantic_chunker.extract_relevant(text, "artificial intelligence", 10000)
    assert result == text


def test_extract_relevant_respects_budget():
    """Should not exceed max_chars even with long text."""
    paragraphs = [f"Paragraph {i}: " + "word " * 50 for i in range(20)]
    text = "\n\n".join(paragraphs)
    result = semantic_chunker.extract_relevant(text, "paragraph", max_chars=500)
    assert len(result) <= 500
