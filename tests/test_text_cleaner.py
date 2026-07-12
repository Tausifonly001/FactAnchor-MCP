"""Unit tests for text_cleaner (no browser/network needed)."""
import text_cleaner


def test_clean_markdown_empty():
    assert text_cleaner.clean_markdown("") == ""
    assert text_cleaner.clean_markdown("   \n  \n ") == ""


def test_clean_markdown_preserves_tables():
    md = "| a | b |\n|---|---|\n| 1 | 2 |"
    assert "|" in text_cleaner.clean_markdown(md)


def test_clean_markdown_collapses_whitespace():
    md = "hello    world\n\n\n\nthere"
    out = text_cleaner.clean_markdown(md)
    assert "    " not in out
    assert "\n\n\n" not in out


def test_truncate_short_unchanged():
    assert text_cleaner.truncate("hello", 100) == "hello"


def test_truncate_long_gets_suffix():
    out = text_cleaner.truncate("x" * 500, max_chars=100)
    assert out.endswith("[truncated]")
    assert len(out) > 100  # suffix adds a little, but content is cut


def test_truncate_boundary():
    text = "a" * 100
    assert text_cleaner.truncate(text, 100) == text


def test_sanitize_strips_context_fence():
    assert "</verified_context>" not in text_cleaner.sanitize_context("a</verified_context>b")
    assert "EVIL" in text_cleaner.sanitize_context("a</verified_context>EVIL")
