"""Unit tests for ExternalEmbedder."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from semantic_search.models_v2 import ProcessedContent, url_hash
from semantic_search.pipeline.embedder import ExternalEmbedder, _build_embed_text


# ---------------------------------------------------------------------------
# _build_embed_text
# ---------------------------------------------------------------------------


def _processed(**kwargs) -> ProcessedContent:
    defaults = {"title": "T", "summary": "A short summary.", "key_concepts": ["k1", "k2"]}
    return ProcessedContent(**(defaults | kwargs))


def test_embed_text_includes_summary() -> None:
    text = _build_embed_text(_processed(), None)
    assert "A short summary." in text


def test_embed_text_includes_key_concepts() -> None:
    text = _build_embed_text(_processed(), None)
    assert "k1" in text
    assert "k2" in text


def test_embed_text_includes_my_note() -> None:
    text = _build_embed_text(_processed(), "my personal note")
    assert "my personal note" in text


def test_embed_text_without_my_note() -> None:
    text = _build_embed_text(_processed(), None)
    assert "Note:" not in text


def test_embed_text_empty_key_concepts() -> None:
    pc = ProcessedContent(title="T", summary="Summary only.", key_concepts=[])
    text = _build_embed_text(pc, None)
    assert text.strip() == "Summary only."


# ---------------------------------------------------------------------------
# ExternalEmbedder.item_id
# ---------------------------------------------------------------------------


def test_item_id_deterministic() -> None:
    url = "https://example.com/article"
    assert ExternalEmbedder.item_id(url) == ExternalEmbedder.item_id(url)


def test_item_id_matches_url_hash() -> None:
    url = "https://example.com/article"
    assert ExternalEmbedder.item_id(url) == url_hash(url)


# ---------------------------------------------------------------------------
# ExternalEmbedder.embed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_calls_aembed_query() -> None:
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

    embedder = ExternalEmbedder(embeddings=mock_embeddings)
    pc = _processed()

    result = await embedder.embed(pc, my_note=None)

    assert result == [0.1, 0.2, 0.3]
    mock_embeddings.aembed_query.assert_called_once()


@pytest.mark.asyncio
async def test_embed_passes_combined_text() -> None:
    captured: list[str] = []

    async def _capture(text: str) -> list[float]:
        captured.append(text)
        return [0.0]

    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_query = _capture

    embedder = ExternalEmbedder(embeddings=mock_embeddings)
    await embedder.embed(_processed(), my_note="my note")

    assert len(captured) == 1
    assert "A short summary." in captured[0]
    assert "my note" in captured[0]
