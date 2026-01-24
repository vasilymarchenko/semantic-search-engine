# Semantic Search Engine - Content-Aware Chunking

A Python library for intelligent document chunking with support for markdown, code, and other content types. This is the foundation for building a semantic search engine that indexes content from multiple sources.

## 🎯 Project Overview

This project implements **content-aware chunking strategies** that intelligently split documents while preserving semantic boundaries. Unlike naive fixed-size chunking, this approach:

- ✅ Respects document structure (headers, code blocks, tables)
- ✅ Maintains semantic coherence within chunks
- ✅ Provides hierarchical context for each chunk
- ✅ Optimizes for vector embedding and search quality

## 📋 Features

- **Markdown Chunking**: Header-based splitting with code block and table preservation
- **Token Estimation**: Approximate token counting for chunk size control
- **Hierarchical Context**: Track section paths for better search results
- **Two-Tier Strategy**:
  - Documents ≤ 600 tokens: Single chunk (document-level embedding)
  - Documents > 600 tokens: Smart chunking with 50-token overlap
- **Type-Safe Models**: Pydantic models for robust data validation
- **CLI Tool**: Test chunking strategies from command line

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher (3.13 recommended)
- pip (Python package manager)

### Installation

1. **Navigate to project directory**:
```cmd
cd c:\Work\Personal\semantic-search-engine
```

2. **Activate virtual environment**:
```cmd
.venv\Scripts\activate
```

3. **Install the package in editable mode**:
```cmd
pip install -e .
```

This will install the package and all dependencies defined in `pyproject.toml`.

## 📦 Project Structure

```
semantic-search-engine/
├── src/
│   └── semantic_search/          # Main package
│       ├── __init__.py           # Package exports
│       ├── models.py             # Pydantic data models
│       ├── chunking/             # Chunking strategies
│       │   ├── __init__.py
│       │   ├── base.py           # Abstract base class
│       │   └── markdown.py       # Markdown chunker
│       └── cli.py                # Command-line interface
├── tests/                        # Unit tests
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_models.py           # Model tests
│   └── test_chunking.py         # Chunking strategy tests
├── docs/                         # Documentation
│   └── semantic-search-engine-plan.md
├── embedding_pipeline_test.py    # Original prototype (reference)
├── pyproject.toml               # Project configuration
├── requirements.txt             # Core dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md                    # This file
```

## 🧪 Testing

### Run all tests:
```cmd
pytest
```

### Run with coverage:
```cmd
pytest --cov=semantic_search --cov-report=html
```

### Run specific test file:
```cmd
pytest tests\test_chunking.py -v
```

### Run tests in verbose mode:
```cmd
pytest -vv
```

## 🔧 Usage

### CLI Tool

Test the chunking strategy on a markdown document:

```cmd
# Use default document (plan.md)
semantic-chunker

# Specify a custom document
semantic-chunker path\to\document.md

# Adjust chunking parameters
semantic-chunker document.md --max-tokens 500 --overlap 60 --verbose
```

### Python API

```python
from semantic_search import MarkdownChunker

# Initialize chunker
chunker = MarkdownChunker(
    token_threshold=600,      # Documents over this size get chunked
    max_chunk_tokens=400,     # Target chunk size
    overlap_tokens=50,        # Overlap for context
    min_chunk_tokens=100      # Minimum viable chunk
)

# Chunk a document
markdown_text = "# My Document\n\nContent here..."
chunks = chunker.chunk_document(markdown_text)

# Inspect results
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}:")
    print(f"  Tokens: {chunk.token_count}")
    print(f"  Section: {' > '.join(chunk.section_path)}")
    print(f"  Types: {[ct.value for ct in chunk.content_types]}")
    print(f"  Text preview: {chunk.text[:100]}...")
```

## 📐 Architecture

### Data Models (Pydantic)

- **`ContentType`**: Enum for content block types (header, code, table, list, paragraph, ASCII art)
- **`ContentBlock`**: Intermediate representation during parsing
- **`Chunk`**: Final output with text, offsets, tokens, and metadata

### Chunking Strategy

1. **Parse**: Break document into logical content blocks
2. **Group**: Combine blocks into chunks respecting boundaries
3. **Overlap**: Add context overlap between adjacent chunks
4. **Metadata**: Track section paths and content types

### Key Design Principles

- **No text duplication**: Store offsets, not duplicated text
- **Content-aware**: Never split mid-code-block or mid-table
- **Hierarchical context**: Maintain section paths for search relevance
- **Extensible**: Easy to add new chunking strategies (code, PDF, etc.)

## 🛠️ Development

### Code Quality

```cmd
# Format code
black src\ tests\

# Lint code
ruff check src\ tests\
```

### Adding a New Chunking Strategy

1. Create new file in `src\semantic_search\chunking\`
2. Inherit from `ChunkingStrategy` base class
3. Implement `chunk_document(text: str) -> list[Chunk]`
4. Add tests in `tests\test_chunking.py`
5. Export from `src\semantic_search\chunking\__init__.py`

Example:

```python
from semantic_search.chunking.base import ChunkingStrategy
from semantic_search.models import Chunk

class CodeChunker(ChunkingStrategy):
    """AST-based chunking for source code."""
    
    def chunk_document(self, text: str) -> list[Chunk]:
        # Your implementation here
        pass
```

## 📊 Performance Characteristics

- **Small documents** (<600 tokens): Single chunk, ~1ms processing
- **Large documents** (>600 tokens): ~10-50ms depending on complexity
- **Memory**: Minimal overhead, processes in single pass
- **Token estimation**: ~4 chars/token (rough approximation)

## 🔮 Future Enhancements

- [ ] Code chunking (AST-based for Python, C#, JavaScript)
- [ ] Email thread-aware chunking
- [ ] PDF section-based chunking
- [ ] Smarter token counting (use tiktoken library)
- [ ] Async/await support for large documents
- [ ] Chunk quality metrics and validation

## 📚 Related Documentation

- [Project Plan](docs\semantic-search-engine-plan.md) - Comprehensive project documentation
- [Original Prototype](embedding_pipeline_test.py) - Initial proof-of-concept

## 🤝 Contributing

This is a personal project, but suggestions are welcome! Please ensure:

- All tests pass (`pytest`)
- Code is formatted (`black`)
- Type hints are used
- New features include tests

## 📝 License

MIT License

## 👤 Author

**Vasyl**

---

**Status**: Phase 1 - Foundation (Content-Aware Chunking) ✅  
**Last Updated**: January 2026
