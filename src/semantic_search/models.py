"""
Data models for content chunking.

Uses Pydantic for validation and type safety.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class ContentType(str, Enum):
    """Types of content blocks in markdown and other documents."""

    HEADER = "header"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    LIST = "list"
    PARAGRAPH = "paragraph"
    ASCII_ART = "ascii_art"


class ContentBlock(BaseModel):
    """
    Represents a logical block of content.

    This is an intermediate representation used during the chunking process.
    """

    model_config = ConfigDict(frozen=False)

    type: ContentType
    content: str
    start_offset: int
    end_offset: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """
    Represents a searchable chunk with context.

    This is the final output of the chunking process, ready for embedding.
    """

    model_config = ConfigDict(frozen=False)

    text: str
    start_offset: int
    end_offset: int
    token_count: int
    section_path: list[str] = Field(
        default_factory=lambda: ["Document"],
        description="Hierarchical path, e.g., ['Phase 1', 'Cosmos DB Setup']",
    )
    content_types: list[ContentType] = Field(
        default_factory=list,
        description="Types of content present in this chunk",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (chunking strategy, flags, etc.)",
    )
