"""
Data models for the Trajectory-2 external inbox pipeline.

Separate from models.py (Phase 1 chunking) — one embedding per external item,
no full-text storage, no chunking.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def url_hash(url: str) -> str:
    """SHA-256 of the URL, truncated to 16 hex chars — used as Cosmos DB id and dedup key."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class RawContent(BaseModel):
    """Output of a ContentExtractor — raw text before LLM processing."""

    model_config = ConfigDict(frozen=True)

    text: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Structured output from LLM interpretation of raw content."""

    model_config = ConfigDict(frozen=True)

    title: str = ""
    summary: str = ""
    key_concepts: list[str] = Field(default_factory=list)
    error: str | None = None  # "insufficient_content" | "invalid_llm_response" | None


class ExternalItem(BaseModel):
    """
    Cosmos DB document for an externally saved URL.

    One embedding per item — the embedding target is summary + key_concepts + my_note.
    Full text is NOT stored; the original URL is the reference back to the source.
    """

    model_config = ConfigDict(frozen=True)

    id: str  # url_hash(source_url)
    type: Literal["external"] = "external"
    user_id: str

    title: str
    summary: str  # 2-3 sentences, Claude-generated
    key_concepts: list[str]  # ["kubernetes", "autoscaling"]
    source_url: str
    source_type: str  # article | video | tweet | telegram_post | pdf
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    my_note: str | None = None  # optional user annotation

    embedding: list[float]
    content_hash: str  # url_hash(source_url) — explicit dedup key

    @classmethod
    def build(
        cls,
        *,
        url: str,
        user_id: str,
        processed: ProcessedContent,
        source_type: str,
        embedding: list[float],
        my_note: str | None = None,
    ) -> ExternalItem:
        item_id = url_hash(url)
        return cls(
            id=item_id,
            user_id=user_id,
            title=processed.title,
            summary=processed.summary,
            key_concepts=processed.key_concepts,
            source_url=url,
            source_type=source_type,
            my_note=my_note,
            embedding=embedding,
            content_hash=item_id,
        )
