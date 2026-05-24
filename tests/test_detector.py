"""Unit tests for URL-based source type detection."""

from __future__ import annotations

import pytest

from semantic_search.sources.detector import SourceType, detect_source_type


@pytest.mark.parametrize(
    "url,expected",
    [
        # --- VIDEO ---
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", SourceType.VIDEO),
        ("https://youtu.be/dQw4w9WgXcQ", SourceType.VIDEO),
        ("https://youtu.be/dQw4w9WgXcQ?t=42", SourceType.VIDEO),
        # YouTube Shorts fall through — no transcript API support in Sprint 1
        ("https://www.youtube.com/shorts/abc123", SourceType.ARTICLE),
        # youtube.com profile / channel — not a watch URL
        ("https://www.youtube.com/@channelname", SourceType.ARTICLE),
        # --- TWEET ---
        ("https://twitter.com/user/status/123456789", SourceType.TWEET),
        ("https://x.com/user/status/987654321", SourceType.TWEET),
        # Twitter profile pages — not tweets
        ("https://twitter.com/user", SourceType.ARTICLE),
        ("https://x.com/user", SourceType.ARTICLE),
        # --- TELEGRAM ---
        ("https://t.me/channelname/123", SourceType.TELEGRAM),
        ("https://t.me/channelname", SourceType.TELEGRAM),
        # --- PDF ---
        ("https://example.com/report.pdf", SourceType.PDF),
        ("https://example.com/report.pdf?v=2", SourceType.PDF),
        ("https://example.com/report.PDF", SourceType.PDF),  # case-insensitive
        # path contains "pdf" in a directory name — not a PDF
        ("https://example.com/some-pdf-guide", SourceType.ARTICLE),
        ("https://example.com/pdf/index.html", SourceType.ARTICLE),
        # --- ARTICLE (default catch-all) ---
        ("https://example.com/blog/my-post", SourceType.ARTICLE),
        ("https://substack.com/p/my-newsletter", SourceType.ARTICLE),
        ("https://github.com/org/repo", SourceType.ARTICLE),
        ("https://news.ycombinator.com/item?id=12345", SourceType.ARTICLE),
        ("https://arxiv.org/abs/2301.00001", SourceType.ARTICLE),
        ("https://medium.com/@author/article-title", SourceType.ARTICLE),
    ],
)
def test_detect_source_type(url: str, expected: SourceType) -> None:
    assert detect_source_type(url) == expected


def test_detect_source_type_returns_source_type_enum() -> None:
    result = detect_source_type("https://example.com")
    assert isinstance(result, SourceType)


def test_article_is_string_compatible() -> None:
    # StrEnum — can be compared directly to strings
    assert detect_source_type("https://example.com") == "article"
    assert detect_source_type("https://youtu.be/abc") == "video"
