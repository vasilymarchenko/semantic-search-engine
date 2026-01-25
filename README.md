# Semantic Search Engine - Ingestion Pipeline

A Python library for intelligent document ingestion with content-aware chunking. This is the foundation for building a semantic search engine that indexes content from multiple sources (web pages, markdown files, and more).

## 🎯 Project Overview

This project implements a complete **ingestion pipeline** that transforms documents from various sources into search-optimized chunks:

1. **Load**: Fetch content from URLs or local files
2. **Process**: Convert HTML to clean markdown and extract metadata
3. **Chunk**: Intelligently split documents while preserving semantic boundaries
4. **Save**: Output normalized markdown and chunks ready for embedding

**Key Features:**
- 🌐 **URL fetching** with async HTTP support
- 🔄 **HTML to Markdown** conversion (removes ads, navigation, footers)
- 📝 **Markdown enrichment** (extract title, stats, metadata)
- ✂️ **Content-aware chunking** (respects headers, code blocks, tables)
- 🏗️ **Hierarchical context tracking**
- ⚙️ **Configurable** chunk size and overlap
- 🧪 **Type-safe** Pydantic models
- 💻 **Unified CLI** for the complete pipeline

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

- **[Chunking Strategy Guide](docs/chunking-guide.md)** - Comprehensive guide to content-aware chunking
- **[Document Processor](docs/processor-implementation-summary.md)** - Details on HTML/markdown processing
- **[Project Plan](docs/semantic-search-engine-plan.md)** - Full system architecture and roadmap

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
Complete Ingestion Pipeline

Process documents from various sources using the unified CLI:

```bash
# Fetch and process a web page
ingestion-cli https://example.com/article

# Process local HTML file
ingestion-cli document.html

# Process markdown file (with enrichment)
ingestion-cli document.md

# Customize output and chunking
ingestion-cli https://example.com -o my_output --max-tokens 600

# Verbose mode with detailed diagnostics
ingestion-cli document.html --verbose
```

**What it does:**
1. ✅ **Loads** content (fetches URL or reads file)
2. ✅ **Processes** to normalized markdown:
   - HTML → Clean markdown (removes nav/ads/footers)
   - Markdown → Enrichment (extracts title, stats)
3. ✅ **Chunks** the markdown intelligently
4. ✅ **Saves** to output directory:
   - `document.md` - Normalized markdown
   - `chunk_1.md`, `chunk_2.md`, ... - Individual chunks
   - `metadata.json` - Statistics and metadata

### Python API

#### Document Processing

```python
from semantic_search.processors import RawDocument, WebPageProcessor

# Process HTML to markdown
raw_doc = RawDocument(
    content=html_string,
    source_type="web",
    url="https://example.com/article"
)

processor = WebPageProcessor(include_enrichment=True)
document = processor.process(raw_doc)

print(document.title)        # Extracted title
print(document.content)      # Clean markdown
print(document.metadata)     # Author, description, etc.
print(document.statistics)   # Word count, reading time, etc.
```

#### URL Fetching

```python
from semantic_search.utils import fetch_url

# Async URL fetching
raw_doc = await fetch_url("https://example.com/article")
```

#### Chunking

```python
from semantic_search.chunking import MarkdownChunker

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

**For detailed usage examples and best practices, see the [documentation](docs/
**For deprocessors/            # Document processors (HTML→MD)
│   ├── utils/                 # URL fetching utilities
│   ├── models.py              # Data models
│   └── ingestion_cli.py       # Unified
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

### Extending the Project

See the [Chunking Strategy Guide](docs/chunking-guide.md) for:
- Adding new content types
- Creating custom chunking strategies
- Best practices and troubleshooting

## 📊 Status & Roadmap✅ | Phase 2 - Document Processing ✅

**Completed:**
- ✅ Content-aware markdown chunking
- ✅ Code block and table preservation
- ✅ Hierarchical context tracking
- ✅ URL fetching (async with aiohttp)
- ✅ HTML to Markdown conversion (with Readability)
- ✅ Markdown enrichment (title, stats, metadata)
- ✅ Unified ingestion CLI
- ✅ Comprehensive test coverage

**In Progress:**
- 🔄 Email processor (Gmail integration)
- 🔄 PDF processor (text extraction)

**Next Steps:**
- [ ] Embedding integration (OpenAI)
- [ ] Vector store implementation (Cosmos DB)
- [ ] Additional source connectors (Telegram, GitHubPDF, Email)
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
