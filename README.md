# Semantic Search Engine - Content-Aware Chunking

A Python library for intelligent document chunking with support for markdown, code, and other content types. This is the foundation for building a semantic search engine that indexes content from multiple sources.

## 🎯 Project Overview

This project implements **content-aware chunking strategies** that intelligently split documents while preserving semantic boundaries. Unlike naive fixed-size chunking, this approach respects document structure (headers, code blocks, tables) and maintains semantic coherence within chunks to optimize for vector embedding and search quality.

**Key Features:**
- 📝 Markdown chunking with header-based splitting
- 🔒 Code block and table preservation (never split)
- 🏗️ Hierarchical context tracking
- ⚙️ Configurable chunk size and overlap
- 🧪 Type-safe Pydantic models
- 💻 CLI tool for testing and validation

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

3. **Install the package**:
```cmd
# Development mode (recommended)
pip install -e .[dev]

# Or production mode (without dev tools)
pip install -e .
```

This installs the package and all dependencies from `pyproject.toml`.

## 📚 Documentation

- **[Chunking Strategy Guide](docs/chunking-guide.md)** - Comprehensive guide to content-aware chunking, architecture, usage examples, and best practices
- **[Project Plan](docs/semantic-search-engine-plan.md)** - Full system architecture and roadmap for the semantic search engine

## 🧪 Testing

Run the test suite to validate functionality:

```cmd
# Run all tests
pytest

# Run with coverage report
pytest --cov=semantic_search --cov-report=html

# Run specific test file
pytest tests\test_chunking.py -v

# Verbose mode
pytest -vv
```

## 🔧 Usage

### Quick Start

Test the chunking strategy using the CLI:

```cmd
# Use default document
semantic-chunker

# Process custom document
semantic-chunker path\to\document.md

# Save chunks to files for inspection
semantic-chunker --save

# Customize parameters
semantic-chunker document.md --max-tokens 500 --overlap 100 --verbose
```

### Python API

```python
from semantic_search import MarkdownChunker

# Create chunker with custom settings
chunker = MarkdownChunker(
    token_threshold=600,
    max_chunk_tokens=400,
    overlap_tokens=50
)

# Chunk a document
chunks = chunker.chunk_document(markdown_text)

# Process results
for chunk in chunks:
    print(f"Section: {' > '.join(chunk.section_path)}")
    print(f"Tokens: {chunk.token_count}")
    print(f"Text: {chunk.text[:100]}...\n")
```

**For detailed usage examples, configuration options, and best practices, see the [Chunking Strategy Guide](docs/chunking-guide.md).**

## 🛠️ Development

### Managing Dependencies

This project uses `pyproject.toml` for dependency management:

```toml
# Add production dependency
dependencies = [
    "pydantic>=2.0.0",
    "new-package>=1.0.0",
]

# Add development dependency
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "new-dev-tool>=1.0.0",
]
```

Then reinstall:
```cmd
pip install -e .[dev]
```

### Code Quality

Format and lint your code:

```cmd
# Format with Black
black src\ tests\

# Lint with Ruff
ruff check src\ tests\
```

### Project Structure

```
semantic-search-engine/
├── src/semantic_search/       # Main package
│   ├── chunking/              # Chunking strategies
│   ├── models.py              # Data models
│   └── cli.py                 # CLI tool
├── tests/                     # Test suite
├── docs/                      # Documentation
├── pyproject.toml             # Project config & dependencies
└── README.md                  # This file
```

### Extending the Project

See the [Chunking Strategy Guide](docs/chunking-guide.md) for:
- Adding new content types
- Creating custom chunking strategies
- Best practices and troubleshooting

## 📊 Status & Roadmap

**Current Phase:** Phase 1 - Foundation (Content-Aware Chunking) ✅

**Completed:**
- ✅ Markdown chunking with structure preservation
- ✅ Code block and table handling
- ✅ Hierarchical context tracking
- ✅ CLI tool with file export
- ✅ Comprehensive test coverage

**Next Steps:**
- [ ] Additional chunking strategies (Code, PDF, Email)
- [ ] Embedding integration (OpenAI)
- [ ] Vector store implementation (Cosmos DB)
- [ ] Search API (.NET)

See the [Project Plan](docs/semantic-search-engine-plan.md) for the complete roadmap.

## 🤝 Contributing

This is a personal project, but suggestions are welcome! Please ensure:- All tests pass (`pytest`)
- Code is formatted (`black`)
- Type hints are used

## 📝 License

MIT License - see [LICENSE](LICENSE)

## 👤 Author

**Vasyl**

---

*Last Updated: January 2026*
