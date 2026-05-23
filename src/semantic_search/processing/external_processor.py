"""
External content processor — Layer 2 of ADR-006.

Turns raw fetched text into structured { title, summary, key_concepts } using
a source-type-specific skill file and Claude Sonnet.
"""

from __future__ import annotations

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from semantic_search.models_v2 import ProcessedContent, RawContent
from semantic_search.processing.skills_loader import SkillsLoader
from semantic_search.sources.detector import SourceType

logger = logging.getLogger(__name__)

# Conservative: 4 chars ≈ 1 token; send first ~4 000 tokens to the model
_MAX_CHARS = 16_000


class ExternalProcessor:
    def __init__(self, llm: BaseChatModel, skills_loader: SkillsLoader) -> None:
        self._llm = llm
        self._skills = skills_loader

    async def process(self, raw: RawContent, source_type: SourceType) -> ProcessedContent:
        """
        Interpret raw content with a source-type-specific skill, fall back to article.md.

        Returns a ProcessedContent with .error set if the LLM signals insufficient content
        or returns malformed JSON.
        """
        skill = await self._skills.load(
            f"sources/{source_type}.md",
            fallback="sources/article.md",
        )

        text = _truncate(raw.text)
        if raw.title:
            text = f"Title: {raw.title}\n\n{text}"

        response = await self._llm.ainvoke(
            [SystemMessage(content=skill), HumanMessage(content=text)]
        )

        raw_content = response.content
        if not isinstance(raw_content, str):
            raw_content = str(raw_content)

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.error(
                "LLM returned non-JSON for source_type=%s: %s",
                source_type,
                raw_content[:300],
            )
            return ProcessedContent(
                title=raw.title or "",
                error="invalid_llm_response",
            )

        if "error" in data:
            return ProcessedContent(error=data["error"])

        return ProcessedContent(
            title=data.get("title", raw.title or ""),
            summary=data.get("summary", ""),
            key_concepts=data.get("key_concepts", []),
        )


def _truncate(text: str) -> str:
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS] + "\n\n[content truncated]"
