"""
Source type detection — deterministic URL pattern matching.

No LLM involved. Fast, zero-cost, zero-latency dispatch to the right extractor.
Covers ADR-006, Layer 1: Content Acquisition.
"""

from __future__ import annotations

import re
from enum import StrEnum


class SourceType(StrEnum):
    ARTICLE = "article"
    VIDEO = "video"
    TWEET = "tweet"
    TELEGRAM = "telegram_post"
    PDF = "pdf"


# Ordered list — first match wins. ARTICLE is the implicit catch-all default.
_PATTERNS: list[tuple[SourceType, list[str]]] = [
    (SourceType.VIDEO, [r"youtube\.com/watch", r"youtu\.be/[^/]"]),
    (SourceType.TWEET, [r"twitter\.com/\w+/status/", r"x\.com/\w+/status/"]),
    (SourceType.TELEGRAM, [r"t\.me/"]),
    (SourceType.PDF, [r"\.pdf(?:$|\?)", r"/download/.*\.pdf"]),
]


def detect_source_type(url: str) -> SourceType:
    """
    Map a URL to an acquisition SourceType via regex patterns.

    Falls back to ARTICLE (HTTP + HTML parser) for all unmatched URLs —
    covers ~90% of web content without any new code.
    """
    for source_type, patterns in _PATTERNS:
        if any(re.search(p, url, re.IGNORECASE) for p in patterns):
            return source_type
    return SourceType.ARTICLE
