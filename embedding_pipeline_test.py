#!/usr/bin/env python3
"""
Embedding Pipeline - Chunking Strategy Test
Tests content-aware chunking on markdown documents
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class ContentType(Enum):
    """Types of content blocks in markdown"""
    HEADER = "header"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    LIST = "list"
    PARAGRAPH = "paragraph"
    ASCII_ART = "ascii_art"


@dataclass
class ContentBlock:
    """Represents a logical block of content"""
    type: ContentType
    content: str
    start_offset: int
    end_offset: int
    metadata: dict  # For storing header level, code language, etc.


@dataclass
class Chunk:
    """Represents a searchable chunk with context"""
    text: str
    start_offset: int
    end_offset: int
    token_count: int
    section_path: List[str]  # e.g., ["Phase 1", "Cosmos DB Setup"]
    content_types: List[ContentType]  # Types of content in this chunk
    metadata: dict


class MarkdownChunker:
    """
    Content-aware markdown chunking strategy
    
    Two-tier approach:
    1. Documents <= 600 tokens: Single chunk (document-level embedding)
    2. Documents > 600 tokens: Smart chunking with 50-token overlap
    
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
        min_chunk_tokens: int = 100
    ):
        self.token_threshold = token_threshold
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens
        
        # Simple token estimation: ~4 chars per token
        self.chars_per_token = 4
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        return len(text) // self.chars_per_token
    
    def chunk_document(self, markdown_text: str) -> List[Chunk]:
        """
        Main chunking entry point
        
        Strategy:
        1. Estimate total tokens
        2. If <= threshold: return single chunk
        3. If > threshold: parse structure and chunk intelligently
        """
        total_tokens = self.estimate_tokens(markdown_text)
        
        print(f"Document length: {len(markdown_text)} chars")
        print(f"Estimated tokens: {total_tokens}")
        
        if total_tokens <= self.token_threshold:
            print("✓ Document under threshold - single chunk strategy")
            return self._create_single_chunk(markdown_text)
        else:
            print("✓ Document over threshold - hierarchical chunking strategy")
            return self._create_hierarchical_chunks(markdown_text)
    
    def _create_single_chunk(self, text: str) -> List[Chunk]:
        """Create a single chunk for small documents"""
        return [Chunk(
            text=text,
            start_offset=0,
            end_offset=len(text),
            token_count=self.estimate_tokens(text),
            section_path=["Document"],
            content_types=[ContentType.PARAGRAPH],  # Generic for whole doc
            metadata={"chunking_strategy": "single_chunk"}
        )]
    
    def _create_hierarchical_chunks(self, text: str) -> List[Chunk]:
        """
        Create chunks respecting document structure
        
        Process:
        1. Parse document into content blocks
        2. Group blocks into chunks respecting boundaries
        3. Add overlap for context
        """
        # Step 1: Parse into content blocks
        blocks = self._parse_content_blocks(text)
        
        print(f"\nParsed {len(blocks)} content blocks:")
        for i, block in enumerate(blocks[:10]):  # Show first 10
            preview = block.content[:50].replace('\n', '\\n')
            print(f"  {i}: {block.type.value:12s} | {preview}...")
        if len(blocks) > 10:
            print(f"  ... and {len(blocks) - 10} more")
        
        # Step 2: Group into chunks
        chunks = self._group_blocks_into_chunks(blocks, text)
        
        print(f"\nCreated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i}: {chunk.token_count} tokens | "
                  f"Section: {' > '.join(chunk.section_path[-2:])}")
        
        return chunks
    
    def _parse_content_blocks(self, text: str) -> List[ContentBlock]:
        """
        Parse markdown into logical content blocks
        
        Detection order (important!):
        1. Code blocks (```...```)
        2. Tables (lines with |)
        3. Headers (##)
        4. Lists (-, *, 1.)
        5. ASCII art (lines with box drawing chars)
        6. Paragraphs (everything else)
        """
        blocks = []
        lines = text.split('\n')
        i = 0
        current_offset = 0
        
        # Track current section for context
        current_headers = []  # Stack of headers: ["# Title", "## Section"]
        
        while i < len(lines):
            line = lines[i]
            line_start = current_offset
            
            # 1. Code block detection
            if line.strip().startswith('```'):
                block, i, current_offset = self._parse_code_block(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue
            
            # 2. Header detection
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2)
                
                # Update header stack
                current_headers = current_headers[:level-1]
                current_headers.append(title)
                
                block = ContentBlock(
                    type=ContentType.HEADER,
                    content=line,
                    start_offset=line_start,
                    end_offset=line_start + len(line) + 1,
                    metadata={
                        "level": level,
                        "title": title,
                        "path": current_headers.copy()
                    }
                )
                blocks.append(block)
                current_offset += len(line) + 1
                i += 1
                continue
            
            # 3. Table detection (simplified - look for | characters)
            if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
                block, i, current_offset = self._parse_table(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue
            
            # 4. List detection
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                block, i, current_offset = self._parse_list(
                    lines, i, current_offset
                )
                blocks.append(block)
                continue
            
            # 5. ASCII art detection (lines with box drawing)
            if re.search(r'[─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬]', line):
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
        self, lines: List[str], start_idx: int, start_offset: int
    ) -> Tuple[ContentBlock, int, int]:
        """Parse a code block (```...```)"""
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
            
            if line.strip() == '```':
                i += 1
                break
            i += 1
        
        content = '\n'.join(content_lines)
        
        return (
            ContentBlock(
                type=ContentType.CODE_BLOCK,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={"language": language}
            ),
            i,
            current_offset
        )
    
    def _parse_table(
        self, lines: List[str], start_idx: int, start_offset: int
    ) -> Tuple[ContentBlock, int, int]:
        """Parse a markdown table"""
        content_lines = []
        current_offset = start_offset
        i = start_idx
        
        # Collect all consecutive lines with |
        while i < len(lines) and '|' in lines[i]:
            content_lines.append(lines[i])
            current_offset += len(lines[i]) + 1
            i += 1
        
        content = '\n'.join(content_lines)
        
        return (
            ContentBlock(
                type=ContentType.TABLE,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={}
            ),
            i,
            current_offset
        )
    
    def _parse_list(
        self, lines: List[str], start_idx: int, start_offset: int
    ) -> Tuple[ContentBlock, int, int]:
        """Parse a list (bulleted or numbered)"""
        content_lines = []
        current_offset = start_offset
        i = start_idx
        
        # Collect consecutive list items (including indented)
        while i < len(lines):
            line = lines[i]
            # List item or indented content
            if (re.match(r'^\s*[-*+]\s+', line) or 
                re.match(r'^\s*\d+\.\s+', line) or
                (line.startswith('  ') and content_lines)):
                content_lines.append(line)
                current_offset += len(line) + 1
                i += 1
            else:
                break
        
        content = '\n'.join(content_lines)
        
        return (
            ContentBlock(
                type=ContentType.LIST,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={}
            ),
            i,
            current_offset
        )
    
    def _parse_ascii_art(
        self, lines: List[str], start_idx: int, start_offset: int
    ) -> Tuple[ContentBlock, int, int]:
        """Parse ASCII art diagram"""
        content_lines = []
        current_offset = start_offset
        i = start_idx
        
        # Collect lines that look like ASCII art
        while i < len(lines):
            line = lines[i]
            if re.search(r'[─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬]', line) or \
               (content_lines and line.startswith(' ' * 3)):
                content_lines.append(line)
                current_offset += len(line) + 1
                i += 1
            else:
                break
        
        content = '\n'.join(content_lines)
        
        return (
            ContentBlock(
                type=ContentType.ASCII_ART,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={}
            ),
            i,
            current_offset
        )
    
    def _parse_paragraph(
        self, lines: List[str], start_idx: int, start_offset: int
    ) -> Tuple[ContentBlock, int, int]:
        """Parse a regular paragraph"""
        content_lines = []
        current_offset = start_offset
        i = start_idx
        
        # Collect consecutive non-empty lines that aren't special blocks
        while i < len(lines):
            line = lines[i]
            
            # Stop at empty line or special blocks
            if (not line.strip() or 
                line.strip().startswith('```') or
                re.match(r'^#{1,6}\s+', line) or
                '|' in line or
                re.match(r'^\s*[-*+]\s+', line) or
                re.match(r'^\s*\d+\.\s+', line)):
                break
            
            content_lines.append(line)
            current_offset += len(line) + 1
            i += 1
        
        content = '\n'.join(content_lines)
        
        return (
            ContentBlock(
                type=ContentType.PARAGRAPH,
                content=content,
                start_offset=start_offset,
                end_offset=current_offset,
                metadata={}
            ),
            i,
            current_offset
        )
    
    def _group_blocks_into_chunks(
        self, blocks: List[ContentBlock], full_text: str
    ) -> List[Chunk]:
        """
        Group content blocks into chunks
        
        Rules:
        - Never split code blocks, tables, or ASCII art
        - Try to keep related content together (same section)
        - Add overlap between chunks for context
        - Respect max chunk size
        - If a single block exceeds max_chunk_tokens, it becomes its own chunk
        """
        chunks = []
        current_chunk_blocks = []
        current_chunk_tokens = 0
        current_section_path = []
        
        for i, block in enumerate(blocks):
            block_tokens = self.estimate_tokens(block.content)
            
            # Update section path if this is a header
            if block.type == ContentType.HEADER:
                current_section_path = block.metadata.get("path", [])
            
            # Special blocks (code, table, ASCII art) must never be split
            is_atomic = block.type in [
                ContentType.CODE_BLOCK,
                ContentType.TABLE,
                ContentType.ASCII_ART
            ]
            
            # If this single block exceeds max size, handle specially
            if block_tokens > self.max_chunk_tokens:
                # Finalize current chunk if exists
                if current_chunk_blocks:
                    chunk = self._finalize_chunk(
                        current_chunk_blocks,
                        current_section_path,
                        full_text
                    )
                    chunks.append(chunk)
                    current_chunk_blocks = []
                    current_chunk_tokens = 0
                
                # Large block becomes its own chunk
                chunk = self._finalize_chunk(
                    [block],
                    current_section_path,
                    full_text
                )
                chunk.metadata["oversized"] = True
                chunk.metadata["reason"] = f"{block.type.value} exceeds max_chunk_tokens"
                chunks.append(chunk)
                continue
            
            # Should we start a new chunk?
            would_exceed = (current_chunk_tokens + block_tokens > self.max_chunk_tokens)
            
            if would_exceed and current_chunk_blocks:
                # Finalize current chunk
                chunk = self._finalize_chunk(
                    current_chunk_blocks,
                    current_section_path,
                    full_text
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_blocks = self._get_overlap_blocks(
                    current_chunk_blocks,
                    self.overlap_tokens
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
                current_chunk_blocks,
                current_section_path,
                full_text
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_blocks(
        self, blocks: List[ContentBlock], target_overlap_tokens: int
    ) -> List[ContentBlock]:
        """Get the last N blocks that fit within overlap token budget"""
        overlap_blocks = []
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
        blocks: List[ContentBlock],
        section_path: List[str],
        full_text: str
    ) -> Chunk:
        """Create a Chunk from a list of ContentBlocks"""
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
                "has_table": ContentType.TABLE in content_types
            }
        )


def main():
    """Test the chunking strategy on the semantic search plan"""
    
    # Read the semantic search plan document
    doc_path = r"c:\Work\Personal\semantic-search-engine\docs\semantic-search-engine-plan.md"
    
    print("=" * 80)
    print("EMBEDDING PIPELINE - CHUNKING STRATEGY TEST")
    print("=" * 80)
    print(f"\nReading document: {doc_path}\n")
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    # Initialize chunker
    chunker = MarkdownChunker(
        token_threshold=600,      # Your threshold from the plan
        max_chunk_tokens=400,     # Target chunk size
        overlap_tokens=50,        # 50-token overlap
        min_chunk_tokens=100      # Minimum viable chunk
    )
    
    # Chunk the document
    print("\n" + "=" * 80)
    print("CHUNKING PROCESS")
    print("=" * 80)
    chunks = chunker.chunk_document(markdown_text)
    
    # Analysis
    print("\n" + "=" * 80)
    print("CHUNKING ANALYSIS")
    print("=" * 80)
    
    print(f"\nTotal chunks created: {len(chunks)}")
    print(f"Average chunk size: {sum(c.token_count for c in chunks) / len(chunks):.0f} tokens")
    print(f"Min chunk size: {min(c.token_count for c in chunks)} tokens")
    print(f"Max chunk size: {max(c.token_count for c in chunks)} tokens")
    
    # Check for oversized chunks
    oversized = [c for c in chunks if c.metadata.get("oversized")]
    if oversized:
        print(f"\n⚠ Oversized chunks (exceed max_chunk_tokens): {len(oversized)}")
        for chunk in oversized:
            print(f"  - {chunk.token_count} tokens: {chunk.metadata.get('reason')}")
    
    # Token distribution
    print(f"\nToken distribution:")
    ranges = [
        (0, 200, "Very small"),
        (200, 400, "Optimal"),
        (400, 600, "Large"),
        (600, 1000, "Very large"),
        (1000, float('inf'), "Oversized")
    ]
    
    for min_t, max_t, label in ranges:
        count = sum(1 for c in chunks if min_t <= c.token_count < max_t)
        if count > 0:
            percentage = (count / len(chunks)) * 100
            print(f"  {label:12s} ({min_t:4d}-{max_t:4.0f} tokens): {count:2d} chunks ({percentage:5.1f}%)")
    
    # Show first 3 chunks in detail
    print("\n" + "=" * 80)
    print("SAMPLE CHUNKS (first 3)")
    print("=" * 80)
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i} ---")
        print(f"Section: {' > '.join(chunk.section_path)}")
        print(f"Tokens: {chunk.token_count}")
        print(f"Offset: {chunk.start_offset}-{chunk.end_offset}")
        print(f"Content types: {[ct.value for ct in chunk.content_types]}")
        print(f"Metadata: {chunk.metadata}")
        print(f"\nText preview (first 200 chars):")
        print(chunk.text[:200].replace('\n', '\n  '))
        print("  ...")
    
    # Check for code block preservation
    print("\n" + "=" * 80)
    print("CODE BLOCK PRESERVATION CHECK")
    print("=" * 80)
    
    code_chunks = [c for c in chunks if c.metadata.get("has_code")]
    print(f"\nChunks containing code blocks: {len(code_chunks)}")
    
    for i, chunk in enumerate(code_chunks[:2]):
        print(f"\n--- Code Chunk {i} ---")
        print(f"Section: {' > '.join(chunk.section_path[-2:])}")
        # Count code block delimiters
        code_start = chunk.text.count("```")
        print(f"Code block delimiters (```): {code_start}")
        print(f"Properly closed: {'✓' if code_start % 2 == 0 else '✗ BROKEN!'}")


if __name__ == "__main__":
    main()
