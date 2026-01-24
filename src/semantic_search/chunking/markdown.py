"""
Markdown-specific chunking strategy.

Implements content-aware chunking that respects markdown structure:
- Headers (hierarchical)
- Code blocks (never split)
- Tables (never split)
- Lists (keep together when possible)
- ASCII art diagrams
"""

import re
from typing import Optional

from semantic_search.chunking.base import ChunkingStrategy
from semantic_search.models import Chunk, ContentBlock, ContentType


class MarkdownChunker(ChunkingStrategy):
    """
    Content-aware markdown chunking strategy.

    Two-tier approach:
    1. Documents <= token_threshold: Single chunk (document-level embedding)
    2. Documents > token_threshold: Smart chunking with overlap

    Smart chunking rules:
    - Preserve code blocks (never split mid-code)
    - Preserve tables (never split mid-table)
    - Respect header hierarchy
    - Keep lists together when possible
    - Maintain context with overlap
    """

    def __init__(
        self,
        token_threshold: int = 600,
        max_chunk_tokens: int = 400,
        overlap_tokens: int = 50,
        min_chunk_tokens: int = 100,
    ):
        """
        Initialize the markdown chunker.

        Args:
            token_threshold: Documents under this size become single chunk
            max_chunk_tokens: Target maximum size for each chunk
            overlap_tokens: Token overlap between chunks for context
            min_chunk_tokens: Minimum viable chunk size
        """
        self.token_threshold = token_threshold
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def chunk_document(self, markdown_text: str) -> list[Chunk]:
        """
        Main chunking entry point.

        Strategy:
        1. Estimate total tokens
        2. If <= threshold: return single chunk
        3. If > threshold: parse structure and chunk intelligently

        Args:
            markdown_text: Complete markdown document text

        Returns:
            List of Chunk objects
        """
        total_tokens = self.estimate_tokens(markdown_text)

        if total_tokens <= self.token_threshold:
            return self._create_single_chunk(markdown_text)
        else:
            return self._create_hierarchical_chunks(markdown_text)

    def _create_single_chunk(self, text: str) -> list[Chunk]:
        """Create a single chunk for small documents."""
        return [
            Chunk(
                text=text,
                start_offset=0,
                end_offset=len(text),
                token_count=self.estimate_tokens(text),
                section_path=["Document"],
                content_types=[ContentType.PARAGRAPH],
                metadata={"chunking_strategy": "single_chunk"},
            )
        ]

    def _create_hierarchical_chunks(self, text: str) -> list[Chunk]:
        """
        Create chunks respecting document structure.

        Process:
        1. Parse document into content blocks
        2. Group blocks into chunks respecting boundaries
        3. Add overlap for context
        """
        blocks = self._parse_content_blocks(text)
        chunks = self._group_blocks_into_chunks(blocks, text)
        return chunks

    def _parse_content_blocks(self, text: str) -> list[ContentBlock]:
        """
        Parse markdown into logical content blocks.

        Detection order (important!):
        1. Code blocks (```...```)
        2. Headers (##)
        3. Tables (lines with |)
        4. Lists (-, *, 1.)
        5. ASCII art (lines with box drawing chars)
        6. Paragraphs (everything else)
        """
        blocks: list[ContentBlock] = []
        lines = text.split("\n")
        i = 0
        current_offset = 0

        # Track current section for context
        current_headers: list[str] = []

        while i < len(lines):
            line = lines[i]
            line_start = current_offset

            # 1. Code block detection
            if line.strip().startswith("```"):
                block, i, current_offset = self._parse_code_block(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue

            # 2. Header detection
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2)

                # Update header stack
                current_headers = current_headers[: level - 1]
                current_headers.append(title)

                block = ContentBlock(
                    type=ContentType.HEADER,
                    content=line,
                    start_offset=line_start,
                    end_offset=line_start + len(line) + 1,
                    metadata={"level": level, "title": title, "path": current_headers.copy()},
                )
                blocks.append(block)
                current_offset += len(line) + 1
                i += 1
                continue

            # 3. Table detection (simplified - look for | characters)
            if "|" in line and i + 1 < len(lines) and "|" in lines[i + 1]:
                block, i, current_offset = self._parse_table(lines, i, current_offset)
                blocks.append(block)
                continue

            # 4. List detection
            if re.match(r"^\s*[-*+]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
                block, i, current_offset = self._parse_list(lines, i, current_offset)
                blocks.append(block)
                continue

            # 5. ASCII art detection (lines with box drawing)
            if re.search(r"[─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬]", line):
                block, i, current_offset = self._parse_ascii_art(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue

            # 6. Regular paragraph (skip empty lines)
            if line.strip():
                block, i, current_offset = self._parse_paragraph(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue

            # Empty line - just skip
            current_offset += len(line) + 1
            i += 1

        return blocks

    def _parse_code_block(
        self, lines: list[str], start_idx: int, start_offset: int
    ) -> tuple[ContentBlock, int, int]:
        """Parse a code block (```...```)."""
        first_line = lines[start_idx]
        language = first_line.strip()[3:].strip() or "text"

        content_lines = [first_line]
        current_offset = start_offset + len(first_line) + 1
        i = start_idx + 1

        # Find closing ```
        while i < len(lines):
            line = lines[i]
            content_lines.append(line)
            current_offset += len(line) + 1

            if line.strip() == "```":
                i += 1
                break
            i += 1

        content = "\n".join(content_lines)

        return (
            ContentBlock(
                type=ContentType.CODE_BLOCK,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={"language": language},
            ),
            i,
            current_offset,
        )

    def _parse_table(
        self, lines: list[str], start_idx: int, start_offset: int
    ) -> tuple[ContentBlock, int, int]:
        """Parse a markdown table."""
        content_lines = []
        current_offset = start_offset
        i = start_idx

        # Collect all consecutive lines with |
        while i < len(lines) and "|" in lines[i]:
            content_lines.append(lines[i])
            current_offset += len(lines[i]) + 1
            i += 1

        content = "\n".join(content_lines)

        return (
            ContentBlock(
                type=ContentType.TABLE,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={},
            ),
            i,
            current_offset,
        )

    def _parse_list(
        self, lines: list[str], start_idx: int, start_offset: int
    ) -> tuple[ContentBlock, int, int]:
        """Parse a list (bulleted or numbered)."""
        content_lines = []
        current_offset = start_offset
        i = start_idx

        # Collect consecutive list items (including indented)
        while i < len(lines):
            line = lines[i]
            # List item or indented content
            if (
                re.match(r"^\s*[-*+]\s+", line)
                or re.match(r"^\s*\d+\.\s+", line)
                or (line.startswith("  ") and content_lines)
            ):
                content_lines.append(line)
                current_offset += len(line) + 1
                i += 1
            else:
                break

        content = "\n".join(content_lines)

        return (
            ContentBlock(
                type=ContentType.LIST,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={},
            ),
            i,
            current_offset,
        )

    def _parse_ascii_art(
        self, lines: list[str], start_idx: int, start_offset: int
    ) -> tuple[ContentBlock, int, int]:
        """Parse ASCII art diagram."""
        content_lines = []
        current_offset = start_offset
        i = start_idx

        # Collect lines that look like ASCII art
        while i < len(lines):
            line = lines[i]
            if re.search(r"[─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬]", line) or (
                content_lines and line.startswith(" " * 3)
            ):
                content_lines.append(line)
                current_offset += len(line) + 1
                i += 1
            else:
                break

        content = "\n".join(content_lines)

        return (
            ContentBlock(
                type=ContentType.ASCII_ART,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={},
            ),
            i,
            current_offset,
        )

    def _parse_paragraph(
        self, lines: list[str], start_idx: int, start_offset: int
    ) -> tuple[ContentBlock, int, int]:
        """Parse a regular paragraph."""
        content_lines = []
        current_offset = start_offset
        i = start_idx

        # Collect consecutive non-empty lines that aren't special blocks
        while i < len(lines):
            line = lines[i]

            # Stop at empty line or special blocks
            if (
                not line.strip()
                or line.strip().startswith("```")
                or re.match(r"^#{1,6}\s+", line)
                or "|" in line
                or re.match(r"^\s*[-*+]\s+", line)
                or re.match(r"^\s*\d+\.\s+", line)
            ):
                break

            content_lines.append(line)
            current_offset += len(line) + 1
            i += 1

        content = "\n".join(content_lines)

        return (
            ContentBlock(
                type=ContentType.PARAGRAPH,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={},
            ),
            i,
            current_offset,
        )

    def _group_blocks_into_chunks(
        self, blocks: list[ContentBlock], full_text: str
    ) -> list[Chunk]:
        """
        Group content blocks into chunks.

        Rules:
        - Never split code blocks, tables, or ASCII art
        - Try to keep related content together (same section)
        - Add overlap between chunks for context
        - Respect max chunk size
        - If a single block exceeds max_chunk_tokens, it becomes its own chunk
        """
        chunks: list[Chunk] = []
        current_chunk_blocks: list[ContentBlock] = []
        current_chunk_tokens = 0
        current_section_path: list[str] = []

        for block in blocks:
            block_tokens = self.estimate_tokens(block.content)

            # Update section path if this is a header
            if block.type == ContentType.HEADER:
                current_section_path = block.metadata.get("path", [])

            # Special blocks (code, table, ASCII art) must never be split
            is_atomic = block.type in [
                ContentType.CODE_BLOCK,
                ContentType.TABLE,
                ContentType.ASCII_ART,
            ]

            # If this single block exceeds max size, handle specially
            if block_tokens > self.max_chunk_tokens:
                # Finalize current chunk if exists
                if current_chunk_blocks:
                    chunk = self._finalize_chunk(
                        current_chunk_blocks, current_section_path, full_text
                    )
                    chunks.append(chunk)
                    current_chunk_blocks = []
                    current_chunk_tokens = 0

                # Large block becomes its own chunk
                chunk = self._finalize_chunk([block], current_section_path, full_text)
                chunk.metadata["oversized"] = True
                chunk.metadata[
                    "reason"
                ] = f"{block.type.value} exceeds max_chunk_tokens"
                chunks.append(chunk)
                continue

            # Should we start a new chunk?
            would_exceed = current_chunk_tokens + block_tokens > self.max_chunk_tokens

            if would_exceed and current_chunk_blocks:
                # Finalize current chunk
                chunk = self._finalize_chunk(
                    current_chunk_blocks, current_section_path, full_text
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_blocks = self._get_overlap_blocks(
                    current_chunk_blocks, self.overlap_tokens
                )
                current_chunk_blocks = overlap_blocks
                current_chunk_tokens = sum(
                    self.estimate_tokens(b.content) for b in overlap_blocks
                )

            # Add current block
            current_chunk_blocks.append(block)
            current_chunk_tokens += block_tokens

        # Don't forget the last chunk
        if current_chunk_blocks:
            chunk = self._finalize_chunk(
                current_chunk_blocks, current_section_path, full_text
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_blocks(
        self, blocks: list[ContentBlock], target_overlap_tokens: int
    ) -> list[ContentBlock]:
        """Get the last N blocks that fit within overlap token budget."""
        overlap_blocks: list[ContentBlock] = []
        overlap_tokens = 0

        # Work backwards from end
        for block in reversed(blocks):
            block_tokens = self.estimate_tokens(block.content)
            if overlap_tokens + block_tokens <= target_overlap_tokens:
                overlap_blocks.insert(0, block)
                overlap_tokens += block_tokens
            else:
                break

        return overlap_blocks

    def _finalize_chunk(
        self,
        blocks: list[ContentBlock],
        section_path: list[str],
        full_text: str,
    ) -> Chunk:
        """Create a Chunk from a list of ContentBlocks."""
        if not blocks:
            raise ValueError("Cannot create chunk from empty blocks")

        start_offset = blocks[0].start_offset
        end_offset = blocks[-1].end_offset

        # Extract text using offsets
        chunk_text = full_text[start_offset:end_offset]

        # Collect content types
        content_types = list(set(block.type for block in blocks))

        return Chunk(
            text=chunk_text,
            start_offset=start_offset,
            end_offset=end_offset,
            token_count=self.estimate_tokens(chunk_text),
            section_path=section_path.copy() if section_path else ["Document"],
            content_types=content_types,
            metadata={
                "block_count": len(blocks),
                "has_code": ContentType.CODE_BLOCK in content_types,
                "has_table": ContentType.TABLE in content_types,
            },
        )
