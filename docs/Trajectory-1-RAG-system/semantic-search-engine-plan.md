# Semantic Search Engine - Project Plan

## Executive Summary

A universal semantic search engine that indexes content from multiple sources (Telegram, Email, Obsidian, GitHub, PDFs) and provides intelligent search capabilities using AI-powered embeddings and vector similarity.

**Core Value Proposition:**
- Single search interface across all information sources
- Semantic search (meaning-based, not just keyword matching)
- Hierarchical document structure preservation
- Extensible architecture for future source types

**Technology Stack:**
- **Backend:** Azure Functions (.NET 8 + Python 3.11)
- **Database:** Azure Cosmos DB (NoSQL with vector search)
- **AI/ML:** LangChain, OpenAI Embeddings, Anthropic Claude
- **Frontend:** React SPA (future phase)

---

## Table of Contents

1. [[#Architecture Overview]]
2. [[#Core Concepts]]
3. [[#Data Model]]
4. [[#Implementation Phases]]
5. [[#Technical Deep Dives]]
6. [[#Cost Optimization]]
7. [[#Development Guidelines]]
8. [[#Success Metrics]]

---

## Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           SOURCE CONNECTORS (Extract)                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • TelegramConnector    • EmailConnector                │   │
│  │  • ObsidianConnector    • GitHubConnector               │   │
│  │  • PDFConnector                                          │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        DOCUMENT PROCESSOR (Transform)                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • Parser        (extract raw text/metadata)            │   │
│  │  • Normalizer    (standardize format)                   │   │
│  │  • Enricher      (add metadata, language detection)     │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         EMBEDDING PIPELINE (Transform + Load)            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • Chunking Strategy  (content-aware splitting)         │   │
│  │  • Embedding Generator (vector creation)                │   │
│  │  • Vector Store Writer (persistence with hierarchy)     │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              VECTOR STORE (Cosmos DB)                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • Documents (full text, no embeddings)                 │   │
│  │  • Chunks (offsets + embeddings)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                          │
                          ▼

┌─────────────────────────────────────────────────────────────────┐
│                      SEARCH API                                  │
├─────────────────────────────────────────────────────────────────┤
│  • Query Processing                                              │
│  • Vector Similarity Search                                      │
│  • Result Ranking & Aggregation                                  │
│  • Metadata Filtering                                            │
└─────────────────────────────────────────────────────────────────┘

                          │
                          ▼

┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React SPA)                          │
├─────────────────────────────────────────────────────────────────┤
│  • Search Interface                                              │
│  • Result Display with Highlighting                              │
│  • Filters (source, date, tags)                                  │
│  • Document Viewer                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **ETL Pattern:** Extract (Connectors) → Transform (Processor + Embeddings) → Load (Store)
2. **Separation of Concerns:** Each layer has single responsibility
3. **Extensibility:** Plugin architecture for new source types
4. **Content-Aware Processing:** Chunking strategies adapt to document type
5. **Zero Text Duplication:** Chunks reference parent documents via offsets
6. **Cost Optimization:** Embed only what you search (chunks, not full documents)

---

## Core Concepts

### 1. Source Connectors

**Purpose:** Extract raw content from external sources

**Responsibilities:**
- Authenticate with source API
- Fetch new/updated content
- Extract metadata (author, timestamp, URL)
- Normalize source-specific formats

**Interface:**
```python
class SourceConnector(ABC):
    @abstractmethod
    async def fetch(self, source_id: str) -> list[RawDocument]:
        """Fetch documents from source"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Establish connection to source"""
        pass
```

**Supported Sources (Phase 1):**
- Telegram channels
- Gmail (specific labels/senders)
- Obsidian vault (markdown files from cloud storage)
- GitHub repositories (code + documentation)
- PDF uploads

---

### 2. Document Processor

**Purpose:** Transform raw source data into normalized document format

**Responsibilities:**
- **Parsing:** Extract structured content from raw formats
- **Normalization:** Convert to common intermediate format
- **Enrichment:** Add metadata (language detection, document type classification)

**Workflow:**
```
Raw HTML email → Parse (extract text) → Normalize (markdown) → Enrich (detect language) → Document
Raw PDF → Parse (OCR if needed) → Normalize (text) → Enrich (metadata) → Document
Raw Markdown → Parse (preserve structure) → Normalize (standard format) → Enrich (headings) → Document
```

**Interface:**
```python
class DocumentProcessor(ABC):
    @abstractmethod
    async def process(self, raw_doc: RawDocument) -> Document:
        """Convert raw document to normalized format"""
        pass
```

---

### 3. Chunking Strategy

**Purpose:** Split documents into searchable chunks using content-aware logic

**Key Principle:** **Semantic Chunking** - respect document structure and meaning

**Terminology:**
- **Naive chunking:** Fixed-size windows (❌ bad for search quality)
- **Structural chunking:** Split by logical boundaries like headers (✅ better)
- **Semantic chunking:** Split by meaning + structure (✅ best)

**Implementation Approaches:**

| Document Type | Chunking Strategy | Boundaries |
|---------------|-------------------|------------|
| Markdown | Header-based | `##` headers, code blocks, lists |
| Code | AST-based | Function/class definitions, docstrings |
| Email | Thread-aware | Subject, quoted replies, signatures |
| PDF | Page/section-based | Paragraphs, sections, tables |

**Interface:**
```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Split document into chunks"""
        pass

class MarkdownChunker(ChunkingStrategy):
    """Respects heading hierarchy, code blocks, lists"""
    pass

class CodeChunker(ChunkingStrategy):
    """Uses AST parsing to split by functions/classes"""
    pass
```

**Configuration:**
- **Chunk size:** 500-1000 characters (configurable per source)
- **Overlap:** 10-20% for context preservation
- **Minimum chunk size:** 100 characters

---

### 4. Embedding Pipeline

**Purpose:** Convert text chunks into vector embeddings for semantic search

**Workflow:**
```
Chunk text → OpenAI API → Embedding vector (1536 dimensions) → Store with chunk
```

**Cost Optimization:**
- ✅ **Embed only chunks** (not full documents)
- ✅ Use document hash to skip re-embedding unchanged content
- ✅ Batch API calls when possible

**Interface:**
```python
class EmbeddingService(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text"""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (more efficient)"""
        pass
```

**Configuration:**
- **Model:** `text-embedding-3-small` (1536 dimensions)
- **Cost:** $0.02 per 1M tokens
- **Batch size:** 100 texts per API call (rate limit optimization)

---

### 5. Vector Store

**Purpose:** Persist documents and chunks with hierarchical structure

**Key Design Decisions:**
- ✅ **Parent-child references** (no text duplication)
- ✅ **Offsets for chunk extraction** (compute on retrieval)
- ✅ **Embeddings only on chunks** (search target)
- ✅ **Document hash** (update detection, deduplication)

**Query Patterns:**
1. **Vector similarity search:** Query embedding → find similar chunks → return with parent references
2. **Metadata filtering:** Filter by source, date, author before vector search
3. **Hybrid search:** Combine vector similarity + keyword matching

---

## Data Model

### Cosmos DB Configuration

**Database:** `semantic-search`  
**Container:** `documents-and-chunks`  
**Partition Key:** `/userId`  
**Indexing:**
- Automatic indexing on all fields
- Vector index on `/embedding` path (chunks only)

**Free Tier Limits:**
- 1000 RU/s throughput
- 25GB storage

---

### Document Schema

**Purpose:** Store full document text and metadata (NO embeddings)

```json
{
  "id": "doc_obs_20240115_note123",
  "type": "document",
  "userId": "vasyl",
  
  "content": {
    "fullText": "The complete original document text...",
    "hash": "sha256:a1b2c3d4e5f6..."
  },
  
  "metadata": {
    "sourceType": "obsidian",
    "sourceUrl": "obsidian://vault/MyNote.md",
    "sourceMetadata": {
      "vaultName": "Personal",
      "filePath": "Notes/MyNote.md",
      "tags": ["tech", "learning"]
    },
    "author": "vasyl",
    "createdAt": "2024-01-15T10:00:00Z",
    "updatedAt": "2024-01-15T12:00:00Z",
    "lastIndexedAt": "2024-01-15T12:05:00Z",
    "language": "en",
    "version": 2
  },
  
  "statistics": {
    "characterCount": 4200,
    "wordCount": 650,
    "chunkCount": 8
  }
}
```

---

### Chunk Schema

**Purpose:** Store chunk references and embeddings (NO text duplication)

```json
{
  "id": "chunk_doc_obs_20240115_note123_0",
  "type": "chunk",
  "userId": "vasyl",
  
  "parentDocId": "doc_obs_20240115_note123",
  "chunkIndex": 0,
  
  "position": {
    "startOffset": 0,
    "endOffset": 500
  },
  
  "embedding": [0.123, -0.456, 0.789, ...],  // 1536-dimensional vector
  
  "metadata": {
    "section": "Introduction",
    "headingPath": ["Chapter 1", "Introduction"],
    "precedingContext": "This chapter introduces...",
    "followingContext": "...continues with examples"
  }
}
```

**Key Fields:**
- **`startOffset` / `endOffset`:** Character positions in `parentDocId.content.fullText`
- **`embedding`:** Vector used for similarity search
- **`headingPath`:** Hierarchical position in document structure
- **`precedingContext` / `followingContext`:** Brief text snippets for context (optional, ~50 chars each)

---

### Source-Specific Metadata Examples

**Telegram:**
```json
"sourceMetadata": {
  "channelName": "DevOps Daily",
  "channelId": "@devops_daily",
  "messageId": 1234567890,
  "messageUrl": "https://t.me/devops_daily/1234567890",
  "authorUsername": "@john_doe"
}
```

**Email:**
```json
"sourceMetadata": {
  "from": "newsletter@example.com",
  "fromName": "DevOps Weekly",
  "subject": "Weekly DevOps Digest #247",
  "messageId": "CAGFHs+uniqueid@mail.gmail.com",
  "threadId": "thread_123",
  "labels": ["Newsletter", "Tech"]
}
```

**GitHub:**
```json
"sourceMetadata": {
  "repository": "microsoft/azure-docs",
  "branch": "main",
  "filePath": "docs/functions/overview.md",
  "commitHash": "a1b2c3d",
  "lastCommitDate": "2024-01-10T08:30:00Z"
}
```

**Obsidian:**
```json
"sourceMetadata": {
  "vaultName": "Personal",
  "filePath": "Notes/AI/RAG-Architecture.md",
  "tags": ["ai", "architecture", "rag"],
  "frontmatter": {
    "created": "2024-01-05",
    "updated": "2024-01-15"
  }
}
```

---

## Implementation Phases

### Phase 1: Foundation - Indexing Pipeline (Python)

**Goal:** Build core indexing capability with one source type (Obsidian)

**Duration:** 2-3 weeks

**Deliverables:**
1. ✅ Cosmos DB setup with vector indexing
2. ✅ ObsidianConnector (read markdown files from cloud storage)
3. ✅ MarkdownProcessor (parse, normalize, enrich)
4. ✅ MarkdownChunker (header-based splitting)
5. ✅ EmbeddingService (OpenAI integration)
6. ✅ VectorStore (Cosmos DB client with parent-child pattern)
7. ✅ End-to-end indexing pipeline (Azure Function)

**Success Criteria:**
- [ ] 10 Obsidian notes indexed successfully
- [ ] Documents stored with hash
- [ ] Chunks stored with embeddings and offsets
- [ ] Vector search returns semantically similar chunks
- [ ] No text duplication (verified manually)

**Project Structure:**
```
indexing-function/
├── function_app.py           # Azure Function entry point
├── requirements.txt          # Dependencies
├── host.json                # Function configuration
├── local.settings.json      # Local secrets (git-ignored)
├── src/
│   ├── connectors/
│   │   ├── base.py          # SourceConnector ABC
│   │   └── obsidian.py      # ObsidianConnector
│   ├── processors/
│   │   ├── base.py          # DocumentProcessor ABC
│   │   └── markdown.py      # MarkdownProcessor
│   ├── chunking/
│   │   ├── base.py          # ChunkingStrategy ABC
│   │   └── markdown.py      # MarkdownChunker
│   ├── embeddings/
│   │   └── openai_service.py
│   ├── storage/
│   │   └── cosmos_store.py
│   ├── models/
│   │   └── document.py      # Pydantic models
│   └── pipeline.py          # IndexingPipeline orchestrator
└── tests/
    ├── test_chunking.py
    ├── test_embeddings.py
    └── test_pipeline.py
```

---

### Phase 2: Additional Source Connectors

**Goal:** Extend indexing to support Telegram, Email, GitHub, PDF

**Duration:** 3-4 weeks (parallel development possible)

**Deliverables:**

**2.1 Telegram Connector**
- TelegramConnector implementation
- Authentication with Telegram API
- Poll channels for new messages
- Store session in Azure Key Vault

**2.2 Email Connector**
- GmailConnector implementation
- OAuth2 authentication flow
- Query Gmail API (specific labels/senders)
- Parse email content (HTML → text)

**2.3 GitHub Connector**
- GitHubConnector implementation
- GitHub API authentication (personal access token)
- Clone/fetch repository content
- Process markdown documentation + code files
- CodeChunker (AST-based splitting for Python, C#, JavaScript)

**2.4 PDF Connector**
- PDFConnector implementation
- Upload mechanism (Azure Blob Storage)
- PDF text extraction (pypdf, pdfplumber)
- OCR for scanned PDFs (Azure AI Document Intelligence)
- Handle tables, images, multi-column layouts

**Success Criteria:**
- [ ] Each connector indexes 10+ documents successfully
- [ ] Source-specific metadata preserved
- [ ] Content-aware chunking works for each type
- [ ] Search returns results from all sources

---

### Phase 3: Search API (.NET)

**Goal:** Provide REST API for semantic search with metadata filtering

**Duration:** 2 weeks

**API Endpoints:**

#### **POST /api/search**
Semantic search with optional filters

**Request:**
```json
{
  "query": "kubernetes autoscaling strategies",
  "limit": 10,
  "filters": {
    "sourceTypes": ["obsidian", "github"],
    "fromDate": "2024-01-01T00:00:00Z",
    "toDate": "2024-01-31T23:59:59Z",
    "tags": ["kubernetes", "devops"]
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "documentId": "doc_obs_20240115_note123",
      "chunkId": "chunk_doc_obs_20240115_note123_2",
      "score": 0.87,
      "text": "KEDA (Kubernetes Event-Driven Autoscaling) enables fine-grained autoscaling...",
      "context": {
        "preceding": "...discussing various scaling approaches.",
        "following": "This is particularly useful for..."
      },
      "metadata": {
        "sourceType": "obsidian",
        "sourceUrl": "obsidian://vault/MyNote.md",
        "section": "Autoscaling Strategies",
        "createdAt": "2024-01-15T10:00:00Z"
      }
    }
  ],
  "totalResults": 45,
  "queryEmbeddingTime": "120ms",
  "searchTime": "85ms"
}
```

#### **GET /api/documents/{documentId}**
Retrieve full document content

**Response:**
```json
{
  "id": "doc_obs_20240115_note123",
  "content": {
    "fullText": "The complete document text...",
    "hash": "sha256:..."
  },
  "metadata": { ... },
  "chunks": [
    {
      "id": "chunk_..._0",
      "startOffset": 0,
      "endOffset": 500,
      "section": "Introduction"
    }
  ]
}
```

#### **GET /api/sources**
List all indexed sources with statistics

**Response:**
```json
{
  "sources": [
    {
      "type": "obsidian",
      "documentCount": 42,
      "lastIndexed": "2024-01-15T12:00:00Z"
    },
    {
      "type": "telegram",
      "documentCount": 156,
      "lastIndexed": "2024-01-15T11:45:00Z"
    }
  ]
}
```

**Project Structure:**
```
search-api/
├── SearchApi.csproj
├── Program.cs
├── Controllers/
│   ├── SearchController.cs
│   └── DocumentsController.cs
├── Services/
│   ├── ISearchService.cs
│   ├── SearchService.cs
│   ├── IEmbeddingService.cs
│   └── EmbeddingService.cs
├── Repositories/
│   ├── ICosmosRepository.cs
│   └── CosmosRepository.cs
├── Models/
│   ├── SearchRequest.cs
│   ├── SearchResponse.cs
│   └── Document.cs
└── Tests/
    ├── SearchControllerTests.cs
    └── SearchServiceTests.cs
```

---

### Phase 4: Frontend (React)

**Goal:** User-friendly search interface with result visualization

**Duration:** 2-3 weeks

**Core Features:**

1. **Search Interface**
   - Search bar with auto-complete (recent queries)
   - Advanced filters (collapsible panel):
     - Source type checkboxes
     - Date range picker
     - Tag selection (multi-select)
   - Sort options (relevance, date)

2. **Results Display**
   - Card-based layout with:
     - Highlighted matching text
     - Source badge (colored by type)
     - Snippet with preceding/following context
     - Relevance score (optional, for debugging)
     - Click → expand to show full document
   - Infinite scroll or pagination
   - "View in source" link (opens Obsidian, Telegram, etc.)

3. **Document Viewer**
   - Modal or side panel
   - Full document content with syntax highlighting (code)
   - Navigation between chunks
   - "Copy" button for text
   - Metadata display (source, date, author)

4. **Statistics Dashboard** (nice-to-have)
   - Total documents indexed by source
   - Search usage metrics
   - Recent activity

**Tech Stack:**
- **Framework:** React 18 + TypeScript
- **State Management:** TanStack Query (React Query)
- **Routing:** React Router v6
- **UI Library:** shadcn/ui or Mantine
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios

**Project Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── FilterPanel.tsx
│   │   ├── ResultCard.tsx
│   │   ├── ResultList.tsx
│   │   └── DocumentViewer.tsx
│   ├── hooks/
│   │   ├── useSearch.ts
│   │   ├── useDocument.ts
│   │   └── useFilters.ts
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── search.ts
│   └── App.tsx
└── package.json
```

---

### Phase 5: Advanced Features (Future)

**Prioritized feature list:**

1. **Relevance Scoring & Ranking**
   - Hybrid search (vector + BM25 keyword matching)
   - Re-ranking with LLM (Claude) for top results
   - Personalized ranking based on user history

2. **Auto-Summarization**
   - Generate summaries for long documents
   - Multi-document summarization (aggregate results)
   - Bullet-point key takeaways

3. **Question Answering**
   - RAG-based Q&A: "What does this document say about X?"
   - Claude generates answer with citations

4. **Smart Notifications**
   - Email digest (weekly summary of new content)
   - Real-time notifications for high-relevance new documents
   - Telegram bot for inline search

5. **Multi-User Support**
   - User authentication (Azure AD B2C)
   - User-specific document collections
   - Shared workspaces (team collaboration)

6. **Export & Integration**
   - Export search results to PDF/Markdown
   - Obsidian plugin (search from within vault)
   - Claude Desktop MCP server (search from chat)

---

## Technical Deep Dives

### 1. Text Deduplication Strategy

**Problem:** Avoid storing document text twice (in document + chunks)

**Solution: Offset-Based Chunk References**

**Storage:**
```
Document: Store fullText ONCE
Chunks: Store ONLY startOffset, endOffset, embedding
```

**Retrieval:**
```python
async def get_chunk_text(chunk_id: str) -> str:
    chunk = await cosmos_client.get_chunk(chunk_id)
    document = await cosmos_client.get_document(chunk.parentDocId)
    
    # Extract text on-the-fly using offsets
    chunk_text = document.content.fullText[
        chunk.position.startOffset:chunk.position.endOffset
    ]
    
    return chunk_text
```

**Trade-offs:**
| Approach | Storage | Retrieval Speed | Updates |
|----------|---------|-----------------|---------|
| **Offsets** (recommended) | ✅ No duplication | ⚠️ Extra lookup | ✅ Single update point |
| Store chunk text | ❌ 50-80% duplication | ✅ Fast | ❌ Multiple updates |

**Verdict:** Offsets are optimal. Cosmos DB is fast enough that extra lookup is negligible.

---

### 2. Update Detection with Document Hashing

**Workflow:**
```python
async def index_document(source_url: str, new_content: str):
    # 1. Compute hash
    new_hash = hashlib.sha256(new_content.encode()).hexdigest()
    
    # 2. Check if document exists
    existing = await cosmos_client.query_one(
        "SELECT * FROM c WHERE c.metadata.sourceUrl = @url",
        {"@url": source_url}
    )
    
    if existing:
        if existing.content.hash == new_hash:
            # 3a. UNCHANGED - Skip re-indexing (save API cost!)
            logger.info(f"Document {source_url} unchanged, skipping")
            return
        else:
            # 3b. CHANGED - Delete old chunks, re-index
            logger.info(f"Document {source_url} modified, reindexing")
            await delete_chunks(existing.id)
            await cosmos_client.delete_document(existing.id)
    
    # 4. Index new/updated document
    document = await process_and_store(source_url, new_content, new_hash)
```

**Benefits:**
- ✅ **Deduplication:** Same content from different sources → same hash (can detect duplicates)
- ✅ **Update detection:** Content changed? Hash changes
- ✅ **Idempotency:** Re-running indexer on unchanged docs = no-op (zero cost)
- ✅ **Cost savings:** Skip embedding API calls for unchanged content

**Hash Algorithm:** SHA-256 (standard, collision-resistant)

---

### 3. Chunking Implementation Details

**Markdown Chunking Strategy:**

```python
class MarkdownChunker(ChunkingStrategy):
    def __init__(
        self,
        max_chunk_size: int = 800,
        overlap: int = 100,
        min_chunk_size: int = 100
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk(self, document: Document) -> list[Chunk]:
        chunks = []
        
        # 1. Split by ## headers first (preserve semantic sections)
        sections = self._split_by_headers(document.content.fullText)
        
        for section in sections:
            # 2. If section is small enough, keep as single chunk
            if len(section.text) <= self.max_chunk_size:
                chunks.append(self._create_chunk(
                    section.text,
                    section.start_offset,
                    section.heading_path
                ))
            else:
                # 3. Section too large - split further with overlap
                sub_chunks = self._split_with_overlap(
                    section.text,
                    section.start_offset,
                    self.max_chunk_size,
                    self.overlap
                )
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_by_headers(self, text: str) -> list[Section]:
        """Split markdown by heading hierarchy"""
        # Use regex to find ## headers
        # Track heading path: ["Chapter 1", "Section 1.2"]
        pass
    
    def _split_with_overlap(
        self,
        text: str,
        base_offset: int,
        max_size: int,
        overlap: int
    ) -> list[Chunk]:
        """Split large section with overlap for context"""
        pass
```

**Code Chunking Strategy:**

```python
class CodeChunker(ChunkingStrategy):
    def chunk(self, document: Document) -> list[Chunk]:
        # Use tree-sitter for AST parsing
        tree = self.parser.parse(document.content.fullText)
        
        chunks = []
        for node in tree.root_node.children:
            if node.type in ['function_definition', 'class_definition']:
                # Keep function/class as single chunk (with docstring)
                chunk_text = document.content.fullText[
                    node.start_byte:node.end_byte
                ]
                
                chunks.append(Chunk(
                    text=chunk_text,
                    start_offset=node.start_byte,
                    end_offset=node.end_byte,
                    metadata={
                        'type': node.type,
                        'name': self._get_node_name(node)
                    }
                ))
        
        return chunks
```

---

### 4. Vector Search Query Optimization

**Cosmos DB Vector Search:**

```python
async def vector_search(
    query: str,
    filters: SearchFilters,
    limit: int = 10
) -> list[SearchResult]:
    # 1. Generate query embedding
    query_embedding = await embedding_service.embed(query)
    
    # 2. Build Cosmos DB query with vector similarity
    sql_query = """
        SELECT 
            c.id,
            c.parentDocId,
            c.position,
            c.metadata,
            VectorDistance(c.embedding, @queryEmbedding) AS score
        FROM c
        WHERE c.type = 'chunk'
          AND c.userId = @userId
    """
    
    # 3. Add metadata filters
    if filters.source_types:
        sql_query += " AND c.sourceType IN (@sourceTypes)"
    
    if filters.from_date:
        sql_query += " AND c.createdAt >= @fromDate"
    
    # 4. Order by similarity, limit results
    sql_query += """
        ORDER BY VectorDistance(c.embedding, @queryEmbedding)
        OFFSET 0 LIMIT @limit
    """
    
    # 5. Execute query
    chunks = await cosmos_client.query(
        sql_query,
        parameters={
            '@queryEmbedding': query_embedding,
            '@userId': current_user_id,
            '@limit': limit,
            '@sourceTypes': filters.source_types,
            '@fromDate': filters.from_date
        }
    )
    
    # 6. Fetch parent documents and reconstruct chunk text
    results = []
    for chunk in chunks:
        doc = await cosmos_client.get_document(chunk.parentDocId)
        chunk_text = doc.content.fullText[
            chunk.position.startOffset:chunk.position.endOffset
        ]
        
        results.append(SearchResult(
            document_id=chunk.parentDocId,
            chunk_id=chunk.id,
            score=chunk.score,
            text=chunk_text,
            metadata=doc.metadata
        ))
    
    return results
```

**Performance Optimization:**
- **Pre-filter with metadata:** Reduce vector search candidates
- **Batch document lookups:** Fetch multiple parent documents in single query
- **Cache frequent queries:** Store recent search results (Redis, optional)
- **Partition key usage:** Always filter by `userId` (partition key)

---

## Cost Optimization

### Cost Breakdown

**Monthly Cost Estimate (100 documents, 4000 chars each):**

| Component | Usage | Cost |
|-----------|-------|------|
| **Cosmos DB** | 25GB storage, 1000 RU/s | $0 (free tier) |
| **Azure Functions** | ~10K executions/month | $0 (free tier) |
| **OpenAI Embeddings** | 100K tokens initial + 10K tokens/week updates | $0.002 + $0.001/week ≈ **$0.006/month** |
| **Anthropic Claude** (future Q&A feature) | ~100 queries/month | ~$0.30/month |
| **Azure Blob Storage** (PDFs) | 1GB storage | ~$0.02/month |
| **Total** | | **~$0.03/month** (without Q&A) |

### Cost Optimization Strategies

#### 1. Embed Only Chunks (NOT Full Documents)

**Why:** You only search against chunk embeddings, never full document embeddings.

**Implementation:**
```python
async def index_document(document: Document):
    # ✅ Store document (no embedding)
    doc_id = await store_document(document)
    
    # ✅ Chunk document
    chunks = chunker.chunk(document)
    
    # ✅ Embed ONLY chunks
    for chunk in chunks:
        chunk.embedding = await embedder.embed(chunk.text)
        await store_chunk(chunk, parent_id=doc_id)
    
    # ❌ NEVER: document.embedding = await embedder.embed(document.content.fullText)
```

**Savings:** 50% of embedding cost (avoid double-embedding same text)

---

#### 2. Use Document Hash to Skip Re-Embedding

**Implementation:**
```python
if existing_doc and existing_doc.content.hash == new_hash:
    logger.info("Document unchanged, skipping embedding")
    return  # Zero API cost!
```

**Savings:** 100% of embedding cost for unchanged documents (most re-indexing runs)

---

#### 3. Batch Embedding API Calls

**OpenAI allows batch embedding:**

```python
async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in single API call (more efficient)"""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts  # Up to 2048 texts per request
    )
    
    return [item.embedding for item in response.data]
```

**Savings:** Reduce HTTP overhead, faster processing

---

#### 4. Choose Right Embedding Model

| Model | Dimensions | Cost per 1M tokens | Use Case |
|-------|------------|-------------------|----------|
| `text-embedding-3-small` | 1536 | $0.02 | ✅ Recommended (best value) |
| `text-embedding-3-large` | 3072 | $0.13 | High-precision search |
| `text-embedding-ada-002` | 1536 | $0.10 | Legacy (avoid) |

**Recommendation:** Start with `text-embedding-3-small` (excellent quality, lowest cost)

---

#### 5. Dimension Reduction (Optional)

OpenAI allows specifying fewer dimensions:

```python
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=512  # Instead of 1536
)
```

**Trade-offs:**
- ✅ 3x smaller storage (2KB vs 6KB per vector)
- ⚠️ Slightly lower search quality
- ❌ Same API cost (tokens still processed)

**Recommendation:** Start with 1536 dimensions. Storage is cheap (Cosmos DB free tier = 25GB).

---

#### 6. Minimize Chunking Overlap

**Overlap creates redundant text:**

```
Text: "ABCDEFGHIJ" (10 chars)

No overlap:
- Chunk 1: "ABCDE" (5 chars)
- Chunk 2: "FGHIJ" (5 chars)
- Total: 10 chars embedded

50% overlap:
- Chunk 1: "ABCDE" (5 chars)
- Chunk 2: "CDEFG" (5 chars)
- Chunk 3: "EFGHIJ" (5 chars)
- Total: 15 chars embedded (50% overhead)
```

**Recommendation:** Use 10-20% overlap (balance context vs cost)

---

### Real-World Cost Projection

**Scenario: 1000 documents (Obsidian notes, emails, Telegram)**

```
Initial indexing:
- 1000 docs × 4000 chars × 0.25 tokens/char = 1M tokens
- Cost: 1M × $0.02/1M = $0.02

Weekly updates (10% documents change):
- 100 docs × 4000 chars × 0.25 tokens/char = 100K tokens
- Cost: 100K × $0.02/1M = $0.002

Monthly cost: $0.02 + (4 weeks × $0.002) = $0.028
Annual cost: $0.34
```

**Conclusion: Embedding cost is negligible, even at scale.**

---

## Development Guidelines

### Code Quality Standards

**Python:**
- **Linting:** `ruff` (modern, fast) or `pylint`
- **Formatting:** `black` (opinionated) or `ruff format`
- **Type Checking:** `mypy` with strict mode
- **Testing:** `pytest` with `pytest-asyncio`

**.NET:**
- **Analyzers:** StyleCop, SonarAnalyzer
- **Formatting:** Built-in `.editorconfig`
- **Testing:** xUnit with FluentAssertions

**TypeScript:**
- **Linting:** ESLint with Airbnb config
- **Formatting:** Prettier
- **Testing:** Vitest or Jest

---

### Configuration Management

**Local Development:**
```
Python: local.settings.json (git-ignored)
.NET: appsettings.Development.json (git-ignored)
React: .env.local (git-ignored)
```

**Committed Templates:**
```
local.settings.template.json
appsettings.template.json
.env.template
```

**Azure (Production):**
- **Azure Key Vault:** Store all secrets
- **Managed Identity:** Functions access Key Vault without keys
- **App Settings:** Reference Key Vault secrets:
  ```
  @Microsoft.KeyVault(SecretUri=https://kv-semantic-search.vault.azure.net/secrets/OpenAI-ApiKey/)
  ```

---

### Git Workflow

**Branch Strategy:**
- `main` - production-ready code (protected)
- `develop` - integration branch
- Feature branches: `feature/obsidian-connector`, `feature/markdown-chunking`

**Commit Messages:** Conventional Commits
```
feat(indexing): add markdown chunking strategy
fix(search): correct offset calculation in chunk retrieval
docs(readme): update setup instructions
refactor(connectors): extract common auth logic
```

**Pull Requests:**
- Must pass CI checks (linting, tests)
- Require 1 approval (if team grows)
- Squash and merge

---

### Testing Strategy

**Unit Tests:**
- Mock external dependencies (Cosmos DB, OpenAI API)
- Test business logic in isolation
- Coverage target: 80%+

**Integration Tests:**
- Test end-to-end flows (indexing pipeline, search API)
- Use test containers for Cosmos DB emulator
- Run in CI/CD pipeline

**Manual Testing Checklist:**
```
Phase 1:
[ ] Index 10 Obsidian notes
[ ] Verify no text duplication (check document + chunks)
[ ] Search query returns relevant chunks
[ ] Chunk text reconstructed correctly from offsets
[ ] Document hash prevents re-indexing unchanged content

Phase 2:
[ ] Each connector indexes 10+ documents
[ ] Source metadata preserved correctly
[ ] Search returns results from all sources

Phase 3:
[ ] Search API filters work (source, date, tags)
[ ] Response includes relevance scores
[ ] Full document retrieval works

Phase 4:
[ ] Frontend displays results with highlighting
[ ] Filters update results correctly
[ ] Document viewer shows full content
```

---

## Success Metrics

### Phase 1 (Foundation)
- ✅ 10+ documents indexed successfully
- ✅ Zero text duplication verified
- ✅ Vector search returns semantically similar results
- ✅ Document hash prevents unnecessary re-indexing
- ✅ Indexing cost under $0.01 for initial 100 docs

### Phase 2 (Multi-Source)
- ✅ All 5 connectors operational (Telegram, Email, Obsidian, GitHub, PDF)
- ✅ 100+ documents across all sources
- ✅ Content-aware chunking quality verified (manual review)
- ✅ Search returns results from all sources

### Phase 3 (Search API)
- ✅ Search API responds in <200ms (p95)
- ✅ Metadata filtering reduces result set effectively
- ✅ Relevance scores correlate with user perception (A/B test)

### Phase 4 (Frontend)
- ✅ Search interface loads in <1s
- ✅ Results display with highlighting
- ✅ "View in source" links work for all source types
- ✅ User can navigate from search → document → source

---

## Next Steps

### Immediate Actions (Week 1)

1. **Azure Setup**
   ```bash
   # Create resource group
   az group create --name rg-semantic-search --location eastus
   
   # Create Cosmos DB (free tier)
   az cosmosdb create \
     --name cosmos-semantic-search \
     --resource-group rg-semantic-search \
     --enable-free-tier true
   
   # Create database and container
   az cosmosdb sql database create \
     --account-name cosmos-semantic-search \
     --resource-group rg-semantic-search \
     --name semantic-search
   
   az cosmosdb sql container create \
     --account-name cosmos-semantic-search \
     --database-name semantic-search \
     --name documents-and-chunks \
     --partition-key-path /userId \
     --throughput 1000
   ```

2. **Local Development Setup**
   ```bash
   # Python function
   cd indexing-function
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   
   # Configure secrets
   cp local.settings.template.json local.settings.json
   # Edit local.settings.json with your API keys
   ```

3. **First Prototype**
   - Implement ObsidianConnector (read 10 markdown files from local folder)
   - Implement MarkdownChunker
   - Integrate OpenAI embeddings
   - Store in Cosmos DB
   - Verify no text duplication

---

## Resources

### Documentation
- [Azure Cosmos DB Vector Search](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search)
- [Azure Functions Python Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

### Libraries
- **Python:** `langchain`, `langchain-openai`, `azure-cosmos`, `pydantic`
- **.NET:** `Microsoft.Azure.Cosmos`, `Azure.AI.OpenAI`
- **React:** `@tanstack/react-query`, `axios`, `shadcn/ui`

---

## Appendix: Architecture Decision Records (ADRs)

### ADR-001: Parent-Child Document Model with Offsets

**Context:** Need to store document chunks without text duplication.

**Decision:** Store full text only in document, chunks reference parent with offsets.

**Consequences:**
- ✅ No text duplication (50-80% storage savings)
- ✅ Single source of truth for document content
- ⚠️ Extra database lookup on chunk retrieval (acceptable overhead)

---

### ADR-002: Embed Only Chunks, Not Full Documents

**Context:** Need to optimize embedding API cost.

**Decision:** Generate embeddings only for chunks (search targets), not full documents.

**Consequences:**
- ✅ 50% cost reduction (avoid double-embedding)
- ✅ Faster indexing (fewer API calls)
- ✅ Search queries only need chunk embeddings

---

### ADR-003: Content-Aware Chunking Strategies

**Context:** Fixed-size chunking breaks semantic boundaries (mid-sentence, mid-code-block).

**Decision:** Use document-type-specific chunking strategies (markdown, code, email).

**Consequences:**
- ✅ Better search quality (semantically coherent chunks)
- ✅ Preserves document structure (headings, code functions)
- ⚠️ More complex implementation (multiple chunkers)

---

### ADR-004: SHA-256 Hashing for Update Detection

**Context:** Need to avoid re-indexing unchanged documents.

**Decision:** Store SHA-256 hash of document text, compare before indexing.

**Consequences:**
- ✅ Zero embedding cost for unchanged documents
- ✅ Enables deduplication across sources
- ✅ Idempotent indexing (safe to re-run)

---

**Status:** Ready for Phase 1 Implementation  
**Last Updated:** January 2025  
**Author:** Vasyl (with Claude)

---

**Good luck! 🚀 Let's build something amazing.**
