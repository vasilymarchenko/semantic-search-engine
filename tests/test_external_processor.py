"""Unit tests for ExternalProcessor — LLM calls are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from semantic_search.models_v2 import ProcessedContent, RawContent
from semantic_search.processing.external_processor import ExternalProcessor, _truncate
from semantic_search.processing.skills_loader import SkillsLoader
from semantic_search.sources.detector import SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_processor(llm_response: str) -> ExternalProcessor:
    mock_response = MagicMock()
    mock_response.content = llm_response

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    mock_loader = AsyncMock(spec=SkillsLoader)
    mock_loader.load = AsyncMock(return_value="You are a summarizer.")

    return ExternalProcessor(llm=mock_llm, skills_loader=mock_loader)


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


def test_truncate_short_text_unchanged() -> None:
    text = "short text"
    assert _truncate(text) == text


def test_truncate_long_text_adds_marker() -> None:
    long_text = "a" * 20_000
    result = _truncate(long_text)
    assert result.endswith("[content truncated]")
    assert len(result) < len(long_text)


def test_truncate_boundary() -> None:
    text = "x" * 16_000
    assert _truncate(text) == text  # exactly at limit — not truncated


# ---------------------------------------------------------------------------
# ExternalProcessor.process
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_valid_json_returns_processed_content() -> None:
    processor = _make_processor(
        '{"title": "My Article", "summary": "Great article.", "key_concepts": ["python"]}'
    )
    raw = RawContent(text="Some article text.")
    result = await processor.process(raw, SourceType.ARTICLE)

    assert isinstance(result, ProcessedContent)
    assert result.title == "My Article"
    assert result.summary == "Great article."
    assert result.key_concepts == ["python"]
    assert result.error is None


@pytest.mark.asyncio
async def test_process_llm_error_response() -> None:
    processor = _make_processor('{"error": "insufficient_content"}')
    raw = RawContent(text="blah blah")
    result = await processor.process(raw, SourceType.ARTICLE)

    assert result.error == "insufficient_content"


@pytest.mark.asyncio
async def test_process_invalid_json_returns_error() -> None:
    processor = _make_processor("This is not JSON at all.")
    raw = RawContent(text="some content")
    result = await processor.process(raw, SourceType.ARTICLE)

    assert result.error == "invalid_llm_response"


@pytest.mark.asyncio
async def test_process_includes_title_in_prompt_when_available() -> None:
    mock_response = MagicMock()
    mock_response.content = '{"title":"T","summary":"S","key_concepts":[]}'

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    mock_loader = AsyncMock(spec=SkillsLoader)
    mock_loader.load = AsyncMock(return_value="skill prompt")

    processor = ExternalProcessor(llm=mock_llm, skills_loader=mock_loader)
    raw = RawContent(text="article body", title="Article Title")

    await processor.process(raw, SourceType.ARTICLE)

    # Verify the title was prepended to the human message
    call_args = mock_llm.ainvoke.call_args[0][0]
    human_message_content = call_args[1].content
    assert "Title: Article Title" in human_message_content


@pytest.mark.asyncio
async def test_process_uses_source_type_skill_path() -> None:
    mock_response = MagicMock()
    mock_response.content = '{"title":"T","summary":"S","key_concepts":[]}'

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    mock_loader = AsyncMock(spec=SkillsLoader)
    mock_loader.load = AsyncMock(return_value="skill prompt")

    processor = ExternalProcessor(llm=mock_llm, skills_loader=mock_loader)
    raw = RawContent(text="transcript text")

    await processor.process(raw, SourceType.VIDEO)

    mock_loader.load.assert_called_once_with(
        "sources/video.md", fallback="sources/article.md"
    )
