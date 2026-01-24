"""
Tests for data models.
"""

import pytest
from pydantic import ValidationError

from semantic_search.models import ContentType, ContentBlock, Chunk


class TestContentType:
    """Tests for ContentType enum."""

    def test_content_type_values(self):
        """Test that all content types have correct values."""
        assert ContentType.HEADER.value == "header"
        assert ContentType.CODE_BLOCK.value == "code_block"
        assert ContentType.TABLE.value == "table"
        assert ContentType.LIST.value == "list"
        assert ContentType.PARAGRAPH.value == "paragraph"
        assert ContentType.ASCII_ART.value == "ascii_art"

    def test_content_type_str_conversion(self):
        """Test that ContentType can be compared with strings."""
        assert ContentType.HEADER == "header"
        assert ContentType.CODE_BLOCK == "code_block"


class TestContentBlock:
    """Tests for ContentBlock model."""

    def test_create_content_block(self):
        """Test creating a valid content block."""
        block = ContentBlock(
            type=ContentType.PARAGRAPH,
            content="Test content",
            start_offset=0,
            end_offset=12,
            metadata={"key": "value"},
        )

        assert block.type == ContentType.PARAGRAPH
        assert block.content == "Test content"
        assert block.start_offset == 0
        assert block.end_offset == 12
        assert block.metadata == {"key": "value"}

    def test_content_block_default_metadata(self):
        """Test that metadata defaults to empty dict."""
        block = ContentBlock(
            type=ContentType.HEADER,
            content="# Header",
            start_offset=0,
            end_offset=8,
        )

        assert block.metadata == {}

    def test_content_block_validation(self):
        """Test that invalid data raises validation error."""
        with pytest.raises(ValidationError):
            ContentBlock(
                type="invalid_type",  # Should be ContentType enum
                content="Test",
                start_offset=0,
                end_offset=4,
            )


class TestChunk:
    """Tests for Chunk model."""

    def test_create_chunk(self):
        """Test creating a valid chunk."""
        chunk = Chunk(
            text="Test chunk text",
            start_offset=0,
            end_offset=15,
            token_count=4,
            section_path=["Main", "Section 1"],
            content_types=[ContentType.PARAGRAPH],
            metadata={"has_code": False},
        )

        assert chunk.text == "Test chunk text"
        assert chunk.token_count == 4
        assert chunk.section_path == ["Main", "Section 1"]
        assert ContentType.PARAGRAPH in chunk.content_types

    def test_chunk_default_values(self):
        """Test that chunk has sensible defaults."""
        chunk = Chunk(
            text="Test",
            start_offset=0,
            end_offset=4,
            token_count=1,
        )

        assert chunk.section_path == ["Document"]
        assert chunk.content_types == []
        assert chunk.metadata == {}

    def test_chunk_multiple_content_types(self):
        """Test chunk with multiple content types."""
        chunk = Chunk(
            text="# Header\n\nParagraph",
            start_offset=0,
            end_offset=20,
            token_count=5,
            content_types=[ContentType.HEADER, ContentType.PARAGRAPH],
        )

        assert len(chunk.content_types) == 2
        assert ContentType.HEADER in chunk.content_types
        assert ContentType.PARAGRAPH in chunk.content_types
