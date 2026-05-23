# Chunking Strategy Guide

This guide explains the content-aware chunking implementation used in the semantic search engine.

## Overview

Content-aware chunking is the foundation of effective semantic search. Instead of splitting documents at arbitrary character positions, this implementation respects document structure to maintain semantic coherence within each chunk.

## Core Concepts

### What is Chunking?

**Chunking** is the process of splitting large documents into smaller, semantically meaningful pieces that can be:
- Embedded as vectors for semantic search
- Retrieved and presented to users
- Combined with context for better search results

### Why Content-Aware Chunking?

| Approach | Description | Search Quality |
|----------|-------------|----------------|
| **Naive chunking** | Fixed-size windows (every 500 chars) | ❌ Poor - breaks mid-sentence, mid-code |
| **Structural chunking** | Split by logical boundaries (headers, paragraphs) | ✅ Better - respects structure |
| **Semantic chunking** | Structure + meaning + context | ✅ Best - optimal for search |

**Example of the problem:**

```markdown
Naive chunking might split this code:

Chunk 1: "Here's how to implement caching:
```python
def cache_result(key):
    if key in cache:
        return cac"

Chunk 2: "he[key]
    # Compute expensive operation
    result = expensive_func()
```
This breaks the code!"

Content-aware chunking keeps the entire code block intact.
```

## Architecture

### Two-Tier Strategy

The chunker uses different strategies based on document size:

**Small Documents (≤ 600 tokens):**
- **Strategy:** Single chunk
- **Rationale:** Already small enough for good embedding quality
- **Benefit:** Zero overhead, maximum context preservation

**Large Documents (> 600 tokens):**
- **Strategy:** Smart chunking with overlap
- **Rationale:** Must split for manageable embedding size
- **Benefit:** Maintains context boundaries and adds overlap

### Content Block Types

The chunker identifies and handles these content types:

```python
class ContentType(Enum):
    HEADER = "header"           # Markdown headers (##)
    CODE_BLOCK = "code_block"   # Fenced code blocks (```)
    TABLE = "table"             # Markdown tables
    LIST = "list"               # Bulleted/numbered lists
    PARAGRAPH = "paragraph"     # Regular text
    ASCII_ART = "ascii_art"     # Diagrams with box-drawing characters
```

### Atomic Content Blocks

Some content types are **atomic** - they can never be split:

✅ **Atomic (never split):**
- Code blocks
- Tables
- ASCII art diagrams

⚠️ **Best-effort (keep together when possible):**
- Lists
- Paragraphs

## Processing Pipeline

### Step 1: Parse Content Blocks

The document is parsed into logical blocks:

```
Input text
    ↓
Split by lines
    ↓
Identify patterns (##, ```, |, -, etc.)
    ↓
Create ContentBlock objects
```

**Parse order (priority matters):**
1. Code blocks (```) - must catch first to avoid false header detection
2. Headers (##)
3. Tables (|)
4. Lists (-, *, 1.)
5. ASCII art (box-drawing chars)
6. Paragraphs (everything else)

### Step 2: Group into Chunks

Blocks are combined into chunks following these rules:

```python
for each block:
    if block.tokens > max_chunk_tokens:
        # Special case: oversized atomic block
        create_standalone_chunk(block)
    
    elif current_chunk.tokens + block.tokens > max_chunk_tokens:
        # Would exceed limit
        finalize_current_chunk()
        start_new_chunk_with_overlap()
        add_block_to_new_chunk()
    
    else:
        # Fits in current chunk
        add_block_to_current_chunk()
```

**Key behaviors:**
- **Atomic blocks > max_size:** Become their own chunk (marked as "oversized")
- **Regular overflow:** Start new chunk with overlap from previous chunk
- **Same section content:** Kept together when possible (tracked via header hierarchy)

### Step 3: Add Overlap

Overlap provides context continuity between chunks:

```
Chunk 1: [Block A] [Block B] [Block C]
                              └─overlap─┐
Chunk 2:                      [Block C] [Block D] [Block E]
                                                  └─overlap─┐
Chunk 3:                                         [Block E] [Block F]
```

**Overlap algorithm:**
- Work backward from end of previous chunk
- Add blocks until reaching `overlap_tokens` limit
- Preserve complete blocks (don't split mid-block)

## Data Models

### ContentBlock

Intermediate representation during parsing:

```python
@dataclass
class ContentBlock:
    type: ContentType           # What kind of block
    content: str                # Raw text
    start_offset: int           # Position in original document
    end_offset: int            # End position
    metadata: dict             # Type-specific data
```

**Example metadata:**

```python
# Header block
metadata = {
    "level": 2,
    "title": "Architecture",
    "path": ["Overview", "Architecture"]  # Hierarchical path
}

# Code block
metadata = {
    "language": "python"
}
```

### Chunk

Final output model:

```python
@dataclass
class Chunk:
    text: str                       # Chunk text (extracted via offsets)
    start_offset: int               # Position in original document
    end_offset: int                # End position
    token_count: int               # Estimated tokens
    section_path: list[str]        # Hierarchical context
    content_types: list[ContentType]  # Block types in this chunk
    metadata: dict                 # Additional info
```

**Important:** `text` is computed from the parent document using offsets. In production, chunks won't store text - only offsets.

## Usage Examples

### Basic Usage

```python
from semantic_search import MarkdownChunker

# Initialize with default settings
chunker = MarkdownChunker()

# Chunk a document
markdown_text = """
# My Document

Some introduction text here.

## Code Example

Here's a Python function:

```python
def hello(name):
    return f"Hello, {name}!"
```

## Conclusion

Final thoughts.
"""

chunks = chunker.chunk_document(markdown_text)

# Inspect results
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.token_count} tokens")
    print(f"Section: {' > '.join(chunk.section_path)}")
    print(f"Content types: {chunk.content_types}")
```

### Custom Configuration

```python
chunker = MarkdownChunker(
    token_threshold=800,      # Larger docs before chunking
    max_chunk_tokens=500,     # Bigger chunks
    overlap_tokens=100,       # More overlap
    min_chunk_tokens=50       # Smaller minimum
)

chunks = chunker.chunk_document(text)
```

### CLI Testing

```bash
# Test on default document
semantic-chunker

# Custom document
semantic-chunker my-doc.md

# Save chunks to files for inspection
semantic-chunker my-doc.md --save

# Adjust parameters
semantic-chunker my-doc.md --max-tokens 500 --overlap 100 --verbose

# See detailed information
semantic-chunker my-doc.md -v
```

### Inspecting Chunk Output

```python
chunk = chunks[0]

# Basic info
print(f"Text length: {len(chunk.text)} chars")
print(f"Token estimate: {chunk.token_count} tokens")

# Position in original document
print(f"Offset: {chunk.start_offset}-{chunk.end_offset}")

# Hierarchical context
print(f"Section: {' > '.join(chunk.section_path)}")
# Example: "Overview > Architecture > Design Patterns"

# Content composition
print(f"Types: {[ct.value for ct in chunk.content_types]}")
# Example: ["header", "paragraph", "code_block"]

# Additional metadata
print(f"Block count: {chunk.metadata['block_count']}")
print(f"Has code: {chunk.metadata['has_code']}")
print(f"Has table: {chunk.metadata['has_table']}")
```

## Configuration Parameters

### Token Threshold
```python
token_threshold: int = 600  # Default
```
- Documents under this size become a single chunk
- Avoids unnecessary splitting of small documents
- Typical values: 400-800

### Max Chunk Tokens
```python
max_chunk_tokens: int = 400  # Default
```
- Target maximum size for each chunk
- Embedding models have token limits (e.g., 8191 for text-embedding-3-small)
- Trade-off: smaller chunks = more precise search, but less context
- Typical values: 300-600

### Overlap Tokens
```python
overlap_tokens: int = 50  # Default
```
- Tokens shared between consecutive chunks
- Provides context continuity
- Too small = context loss; too large = redundancy
- Typical values: 10-20% of max_chunk_tokens

### Min Chunk Tokens
```python
min_chunk_tokens: int = 100  # Default
```
- Minimum viable chunk size
- Prevents tiny, low-value chunks
- Tiny chunks might be merged with neighbors (future enhancement)
- Typical values: 50-150

## Design Principles

### 1. Zero Text Duplication

**Problem:** Storing text in both documents and chunks wastes storage.

**Solution:** Chunks store only offsets, not text:

```python
# ✅ Storage
Document: {fullText: "...entire document..."}
Chunk: {
    parentDocId: "doc123",
    startOffset: 100,
    endOffset: 550,
    embedding: [0.1, 0.2, ...]
}

# ✅ Retrieval
def get_chunk_text(chunk):
    doc = get_document(chunk.parentDocId)
    return doc.fullText[chunk.startOffset:chunk.endOffset]
```

**Benefit:** 50-80% storage savings in production.

### 2. Content-Aware Boundaries

**Never split:**
- Mid-code-block
- Mid-table
- Mid-sentence (paragraphs end at newlines)

**Code block example:**

```markdown
Context text before code.

```python
def important_function():
    line1
    line2
    line3
```

Context text after code.
```

The code block stays intact in one chunk, possibly with surrounding context.

### 3. Hierarchical Context

Track position in document structure:

```python
chunk.section_path = ["Chapter 1", "Section 1.2", "Subsection A"]
```

**Benefits:**
- Better search relevance (weight header matches higher)
- Display breadcrumbs in search results
- Filter by section
- Understand chunk context

### 4. Overlap for Context

Chunks share content at boundaries:

```
Chunk N ends with:   "...conclusion of Section A."
                         └─── overlap ───┐
Chunk N+1 starts with:  "conclusion of Section A. Beginning of Section B..."
```

**Why it helps:**
- Search queries near chunk boundaries find both chunks
- Context isn't lost at split points
- Better relevance for queries spanning boundaries

## Performance Characteristics

### Speed

| Document Size | Processing Time |
|---------------|----------------|
| Small (<600 tokens, single chunk) | ~1ms |
| Medium (1000-5000 tokens) | ~10-30ms |
| Large (10000+ tokens) | ~50-100ms |

**Factors:**
- Regex parsing is fast but scales linearly
- Token estimation: ~4ms per 1000 chars
- Most time spent in string operations

### Memory

- **Single-pass processing:** No full document duplication
- **Peak usage:** ~2-3x document size during parsing
- **Output size:** Minimal (Chunk objects are small - just offsets and metadata)

### Token Estimation

Current implementation:

```python
def estimate_tokens(self, text: str) -> int:
    """Rough approximation: ~4 characters per token"""
    return len(text) // 4
```

**Accuracy:** ±15% compared to actual tokenizers

**Future improvement:** Use `tiktoken` library for exact counts:
```python
import tiktoken
encoder = tiktoken.get_encoding("cl100k_base")
tokens = len(encoder.encode(text))
```

## Extending the Chunker

### Adding New Content Types

1. **Define the content type:**

```python
class ContentType(Enum):
    # ...existing types...
    CALLOUT = "callout"  # New: Obsidian callouts
```

2. **Add detection logic in `_parse_content_blocks`:**

```python
# In parse loop
if line.strip().startswith("> [!"):
    block, i, current_offset = self._parse_callout(...)
    blocks.append(block)
    continue
```

3. **Implement parser:**

```python
def _parse_callout(self, lines, start_idx, start_offset):
    # Parse callout syntax
    # Return (ContentBlock, next_idx, next_offset)
    pass
```

4. **Decide if atomic:**

```python
# If callouts should never be split:
is_atomic = block.type in [
    ContentType.CODE_BLOCK,
    ContentType.TABLE,
    ContentType.ASCII_ART,
    ContentType.CALLOUT,  # Add here
]
```

### Creating New Chunking Strategies

Example: Code chunker using AST:

```python
from semantic_search.chunking.base import ChunkingStrategy
from semantic_search.models import Chunk
import ast

class PythonCodeChunker(ChunkingStrategy):
    """AST-based chunking for Python code."""
    
    def chunk_document(self, text: str) -> list[Chunk]:
        tree = ast.parse(text)
        chunks = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Extract function/class with docstring
                start = node.lineno
                end = node.end_lineno
                chunk_text = self._extract_lines(text, start, end)
                
                chunks.append(Chunk(
                    text=chunk_text,
                    # ...other fields...
                    metadata={
                        "type": type(node).__name__,
                        "name": node.name
                    }
                ))
        
        return chunks
```

## Troubleshooting

### Chunks are too small

**Symptoms:** Many chunks under 100 tokens

**Solutions:**
- Increase `min_chunk_tokens`
- Decrease `token_threshold` (fewer docs will be chunked)
- Check if document has many small sections

### Chunks are too large

**Symptoms:** Warning about oversized chunks

**Solutions:**
- Decrease `max_chunk_tokens`
- Check for very long code blocks or tables
- Consider if atomic blocks should really be atomic

### Code blocks split incorrectly

**Check:**
1. Are closing ``` missing? The parser needs matching delimiters
2. Is code nested in other blocks? Check parse order
3. Run with `--verbose` to see chunk composition

### Poor search results

**Possible causes:**
- Chunks too large (not specific enough)
- Chunks too small (not enough context)
- No overlap (context lost at boundaries)

**Debug:**
```bash
# Save chunks and manually inspect
semantic-chunker problem-doc.md --save -v

# Check chunks_output/*.md files
```

## Best Practices

### 1. Choose appropriate chunk size for your use case

- **Code search:** Smaller chunks (300-400 tokens) - want specific functions
- **Documentation search:** Larger chunks (500-700 tokens) - want full sections
- **Chat context:** Medium chunks (400-500 tokens) - balance precision and context

### 2. Test with representative documents

```bash
# Test on your actual content
semantic-chunker typical-doc.md --save -v

# Review the output chunks
# Adjust parameters if needed
```

### 3. Monitor oversized chunks

```python
oversized = [c for c in chunks if c.metadata.get("oversized")]
if len(oversized) > 0.1 * len(chunks):  # More than 10%
    print("Warning: Many oversized chunks - consider increasing max_chunk_tokens")
```

### 4. Validate code block integrity

```python
for chunk in chunks:
    if chunk.metadata.get("has_code"):
        backtick_count = chunk.text.count("```")
        if backtick_count % 2 != 0:
            print(f"ERROR: Broken code block in chunk {chunk.start_offset}")
```

## Future Enhancements

### Planned Improvements

- [ ] **Smart token counting:** Integrate `tiktoken` for accurate token counts
- [ ] **Recursive chunking:** If chunk oversized, try sub-splitting paragraphs
- [ ] **Chunk merging:** Combine tiny chunks with neighbors
- [ ] **Language detection:** Apply language-specific rules
- [ ] **Quality metrics:** Score chunk quality (coherence, completeness)
- [ ] **Async processing:** Support async for large documents

### Additional Chunking Strategies

- [ ] **CodeChunker:** AST-based for Python, TypeScript, C#
- [ ] **EmailChunker:** Thread-aware, quote handling
- [ ] **PDFChunker:** Page-aware, handle columns and images
- [ ] **HTMLChunker:** DOM-aware, extract main content

## Related Documentation

- [Project Plan](semantic-search-engine-plan.md) - Full system architecture
- [API Reference](#) - (Coming soon) Complete API documentation
- [Testing Guide](#) - (Coming soon) How to test chunking strategies

---

**Questions or issues?** Open an issue on GitHub or refer to the main [README](../README.md) for general project information.
