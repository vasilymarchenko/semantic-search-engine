"""
Content acquisition extractors — Layer 1 of ADR-006.

Each extractor fetches raw bytes/text from a URL.
No LLM involved — deterministic, fast, zero token cost.

Sprint 1:  ArticleExtractor (reuses Phase 1 WebPageProcessor)
Sprint 2:  YouTubeExtractor, PDFExtractor
Sprint 3:  TweetExtractor, TelegramExtractor
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol, runtime_checkable

from semantic_search.models_v2 import RawContent
from semantic_search.sources.detector import SourceType

logger = logging.getLogger(__name__)


@runtime_checkable
class ContentExtractor(Protocol):
    """Structural interface for source-specific content acquisition."""

    async def extract(self, url: str) -> RawContent: ...


# ---------------------------------------------------------------------------
# Sprint 1 — ArticleExtractor
# ---------------------------------------------------------------------------


class ArticleExtractor:
    """
    HTTP fetch → readability → markdown.

    Reuses existing fetch_url + WebPageProcessor from Phase 1 — no new code.
    Default extractor covering articles, blogs, docs, Substack, newsletters,
    GitHub READMEs — ~90% of web content.
    """

    async def extract(self, url: str) -> RawContent:
        from semantic_search.processors.web import WebPageProcessor
        from semantic_search.utils.fetcher import fetch_url

        raw_doc = await fetch_url(url)
        processor = WebPageProcessor(include_enrichment=False)
        doc = processor.process(raw_doc)

        return RawContent(
            text=doc.content,
            title=doc.title,
            metadata=doc.metadata,
        )


# ---------------------------------------------------------------------------
# Sprint 2 — YouTubeExtractor
# ---------------------------------------------------------------------------


class YouTubeExtractor:
    """
    youtube-transcript-api → concatenated transcript text.

    The API is synchronous; it runs in a thread pool via asyncio.to_thread.
    Falls back to ArticleExtractor if the transcript is unavailable.
    """

    async def extract(self, url: str) -> RawContent:
        from youtube_transcript_api import (  # type: ignore[import-untyped]
            NoTranscriptFound,
            TranscriptsDisabled,
            YouTubeTranscriptApi,
        )

        video_id = self._parse_video_id(url)

        try:
            transcript_list = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript, video_id
            )
        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning("No transcript for %s, falling back to ArticleExtractor", url)
            return await ArticleExtractor().extract(url)

        text = " ".join(segment["text"] for segment in transcript_list)
        return RawContent(text=text, metadata={"video_id": video_id})

    @staticmethod
    def _parse_video_id(url: str) -> str:
        import re

        patterns = [r"youtu\.be/([^?&/]+)", r"[?&]v=([^?&]+)"]
        for pattern in patterns:
            if m := re.search(pattern, url):
                return m.group(1)
        raise ValueError(f"Cannot parse video ID from URL: {url!r}")


# ---------------------------------------------------------------------------
# Sprint 2 — PDFExtractor
# ---------------------------------------------------------------------------


class PDFExtractor:
    """Download PDF over HTTP then extract text with pypdf (runs in thread pool)."""

    async def extract(self, url: str) -> RawContent:
        import io

        import aiohttp
        import pypdf  # type: ignore[import-untyped]

        async with aiohttp.ClientSession() as session:
            async with asyncio.timeout(60.0):
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

        def _read_pdf(raw: bytes) -> str:
            reader = pypdf.PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        text = await asyncio.to_thread(_read_pdf, data)
        return RawContent(text=text)


# ---------------------------------------------------------------------------
# Registry — SourceType → extractor instance
# ---------------------------------------------------------------------------

_REGISTRY: dict[SourceType, ContentExtractor] = {
    SourceType.ARTICLE: ArticleExtractor(),
    SourceType.VIDEO: YouTubeExtractor(),
    SourceType.PDF: PDFExtractor(),
    # TWEET and TELEGRAM added in Sprint 3
}

_FALLBACK: ContentExtractor = ArticleExtractor()


def get_extractor(source_type: SourceType) -> ContentExtractor:
    """Return the registered extractor for a source type, or ArticleExtractor as fallback."""
    return _REGISTRY.get(source_type, _FALLBACK)
