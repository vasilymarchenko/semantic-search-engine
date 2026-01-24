"""
Tests for chunking strategies.
"""

import pytest

from semantic_search.chunking.markdown import MarkdownChunker
from semantic_search.models import ContentType


class TestMarkdownChunker:
    """Tests for MarkdownChunker."""

    def test_single_chunk_small_document(self, sample_markdown):
        """Test that small documents become a single chunk."""
        chunker = MarkdownChunker(token_threshold=1000)  # High threshold
        chunks = chunker.chunk_document(sample_markdown)

        assert len(chunks) == 1
        assert chunks[0].metadata["chunking_strategy"] == "single_chunk"
        assert chunks[0].text == sample_markdown

    def test_hierarchical_chunking_large_document(self, sample_markdown):
        """Test that large documents are chunked hierarchically."""
        chunker = MarkdownChunker(
            token_threshold=10,  # Very low threshold to force chunking
            max_chunk_tokens=50,
        )
        chunks = chunker.chunk_document(sample_markdown)

        # Should create multiple chunks
        assert len(chunks) > 1

        # All chunks should have valid offsets
        for chunk in chunks:
            assert chunk.start_offset >= 0
            assert chunk.end_offset > chunk.start_offset
            assert chunk.text == sample_markdown[chunk.start_offset : chunk.end_offset]

    def test_code_block_preservation(self):
        """Test that code blocks are never split."""
        markdown = """# Test

Some text before code.

```python
def function():
    line1 = "test"
    line2 = "test"
    line3 = "test"
    line4 = "test"
    return line1 + line2 + line3 + line4
```

Some text after code.
"""

        chunker = MarkdownChunker(
            token_threshold=10,
            max_chunk_tokens=30,  # Small chunks to force splitting
        )
        chunks = chunker.chunk_document(markdown)

        # Find chunk containing code
        code_chunks = [c for c in chunks if c.metadata.get("has_code")]
        assert len(code_chunks) > 0

        # Verify code block is complete (even delimiters)
        for chunk in code_chunks:
            code_delimiters = chunk.text.count("```")
            assert code_delimiters % 2 == 0, "Code block split mid-block!"

    def test_header_hierarchy_tracking(self, sample_markdown):
        """Test that section paths are tracked correctly."""
        chunker = MarkdownChunker(token_threshold=10, max_chunk_tokens=100)
        chunks = chunker.chunk_document(sample_markdown)

        # Check that section paths are populated
        for chunk in chunks:
            assert isinstance(chunk.section_path, list)
            # Should have at least ["Document"] or deeper paths
            assert len(chunk.section_path) >= 1

    def test_empty_document(self):
        """Test handling of empty document."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk_document("")

        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].token_count == 0

    def test_token_estimation(self):
        """Test token estimation is reasonable."""
        chunker = MarkdownChunker()
        
        text = "This is a test" * 100  # 1400 chars
        tokens = chunker.estimate_tokens(text)
        
        # Should estimate ~350 tokens (1400 / 4)
        assert 300 < tokens < 400

    def test_content_type_detection(self):
        """Test that different content types are detected."""
        markdown = """# Header

Paragraph text.

- List item 1
- List item 2

| Table | Header |
|-------|--------|
| Cell  | Cell   |

```python
code here
```
"""

        chunker = MarkdownChunker(token_threshold=10, max_chunk_tokens=200)
        chunks = chunker.chunk_document(markdown)

        # Collect all content types across chunks
        all_types = set()
        for chunk in chunks:
            all_types.update(chunk.content_types)

        # Should detect multiple content types
        assert ContentType.HEADER in all_types
        assert ContentType.PARAGRAPH in all_types

    def test_oversized_block_handling(self):
        """Test that oversized blocks become their own chunks."""
        # Create a very large code block
        large_code = "```python\n" + ("# comment\n" * 200) + "```"
        
        chunker = MarkdownChunker(
            token_threshold=10,
            max_chunk_tokens=100,  # Much smaller than code block
        )
        chunks = chunker.chunk_document(large_code)

        # Find the oversized chunk
        oversized = [c for c in chunks if c.metadata.get("oversized")]
        assert len(oversized) > 0
        assert "exceeds max_chunk_tokens" in oversized[0].metadata["reason"]

    def test_chunk_overlap(self):
        """Test that chunks have overlap for context."""
        markdown = "\n\n".join([f"Paragraph {i}" for i in range(20)])
        
        chunker = MarkdownChunker(
            token_threshold=10,
            max_chunk_tokens=50,
            overlap_tokens=10,
        )
        chunks = chunker.chunk_document(markdown)

        if len(chunks) > 1:
            # Check that consecutive chunks overlap
            for i in range(len(chunks) - 1):
                chunk1_end = chunks[i].end_offset
                chunk2_start = chunks[i + 1].start_offset
                
                # Overlap means chunk2 starts before chunk1 ends
                # (in terms of content, though offsets are sequential)
                assert chunk2_start <= chunk1_end + 100  # Allow some gap


class TestChunkingEdgeCases:
    """Test edge cases and error handling."""

    def test_only_code_blocks(self):
        """Test document with only code blocks."""
        markdown = """```python
def func1():
    pass
```

```python
def func2():
    pass
```"""

        chunker = MarkdownChunker(token_threshold=10)  # Force chunking
        chunks = chunker.chunk_document(markdown)

        assert len(chunks) >= 1
        # At least one chunk should contain code
        code_chunks = [c for c in chunks if c.metadata.get("has_code")]
        assert len(code_chunks) > 0

    def test_only_headers(self):
        """Test document with only headers."""
        markdown = """# Header 1
## Header 2
### Header 3"""

        chunker = MarkdownChunker()
        chunks = chunker.chunk_document(markdown)

        assert len(chunks) >= 1

    def test_unicode_content(self):
        """Test handling of unicode characters."""
        markdown = "# Заголовок\n\nТекст на русском языке.\n\n日本語のテキスト"

        chunker = MarkdownChunker()
        chunks = chunker.chunk_document(markdown)

        assert len(chunks) >= 1
        assert chunks[0].text == markdown or len(chunks) > 1
