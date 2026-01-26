# Phase 1 Implementation Plan: Embeddings, Storage & Complete Pipeline

**Project:** Semantic Search Engine  
**Phase:** 1 - Core Indexing Infrastructure  
**Duration:** 4-6 weeks  
**Status:** Ready to implement  
**Created:** January 2026

---

## 📋 Executive Summary

This plan completes Phase 1 by implementing:

1. **Embedding Generation** - OpenAI integration with cost optimization
2. **Vector Store Abstraction** - Provider-agnostic storage layer
3. **Complete Ingestion Pipeline** - End-to-end document indexing
4. **Update Detection** - Hash-based change tracking
5. **Testing & Validation** - Comprehensive test suite

**Key Principle:** Storage abstraction allows switching between Cosmos DB, Pinecone, Weaviate, or custom solutions without changing application code.

---

## 🎯 Success Criteria

By the end of this implementation, you will have:

- [ ] Documents indexed with embeddings stored in vector database
- [ ] Semantic search returning relevant results
- [ ] Hash-based update detection working (no re-indexing unchanged docs)
- [ ] CLI supporting full pipeline: `ingestion-cli <url> --embed --store`
- [ ] Storage provider can be swapped via configuration
- [ ] Cost tracking for embedding API calls
- [ ] >80% test coverage for new code

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │  Fetch   │ ─> │ Process  │ ─> │  Chunk   │                 │
│  │  (URL)   │    │ (MD/HTML)│    │ (Smart)  │                 │
│  └──────────┘    └──────────┘    └──────────┘                 │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         EMBEDDING SERVICE                               │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • Batch processing                                     │   │
│  │  • Cost tracking & logging                              │   │
│  │  • Retry logic for rate limits                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │    VECTOR STORE ABSTRACTION (Repository Pattern)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         DOCUMENT HASH REGISTRY                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Implementation Plan

### Week 1: Embedding Service

#### 1.1 Dependencies & Configuration

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "openai>=1.0.0",
    "tiktoken>=0.5.0",
    "structlog>=24.0.0",
    "tenacity>=8.0.0",
]

[project.optional-dependencies]
cosmos = [
    "azure-cosmos>=4.5.0",
    "azure-identity>=1.15.0",
]
dev = [
    # ... existing dev dependencies ...
    "pytest-mock>=3.12.0",
]
```

Create `.env.template`:

```bash
# .env.template - Copy to .env and fill in your values

# Embedding Configuration
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_RETRIES=3

# Vector Store Provider (cosmos|pinecone|weaviate|local)
VECTOR_STORE_PROVIDER=cosmos
USER_ID=vasyl

# Cosmos DB Configuration
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-key-here
COSMOS_DATABASE=semantic-search
COSMOS_CONTAINER=documents-and-chunks

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### 1.2 Embedding Service Implementation

**Create embedding service:**

```python
# src/semantic_search/embeddings/__init__.py

from .service import EmbeddingService, EmbeddingResult
from .models import EmbeddingStats

__all__ = ["EmbeddingService", "EmbeddingResult", "EmbeddingStats"]
```

```python
# src/semantic_search/embeddings/models.py

from pydantic import BaseModel, Field
from datetime import datetime


class EmbeddingStats(BaseModel):
    """Statistics for embedding operations"""
    
    total_chunks: int = 0
    total_tokens: int = 0
    api_calls: int = 0
    estimated_cost: float = 0.0
    skipped_small_docs: int = 0
    processing_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def add_tokens(self, tokens: int, model: str = "text-embedding-3-small"):
        """Add tokens and calculate cost"""
        self.total_tokens += tokens
        
        # Pricing per 1M tokens (as of Jan 2025)
        pricing = {
            "text-embedding-3-small": 0.02,
            "text-embedding-3-large": 0.13,
            "text-embedding-ada-002": 0.10,
        }
        
        cost_per_million = pricing.get(model, 0.02)
        self.estimated_cost = (self.total_tokens / 1_000_000) * cost_per_million


class EmbeddingResult(BaseModel):
    """Result from embedding operation"""
    
    chunk_id: str
    embedding: list[float]
    token_count: int
    model: str
```

```python
# src/semantic_search/embeddings/service.py

import asyncio
import time
from typing import List, Tuple
import tiktoken
from openai import OpenAI, AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

from ..config import settings
from ..chunking.models import Chunk
from .models import EmbeddingStats, EmbeddingResult

logger = structlog.get_logger()


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI API.
    
    Features:
    - Batch processing for efficiency
    - Two-tier optimization (skip small docs)
    - Automatic retry on rate limits
    - Cost tracking
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
    ):
        self.api_key = api_key or settings.embedding.openai_api_key
        self.model = model or settings.embedding.embedding_model
        self.batch_size = batch_size or settings.embedding.batch_size
        self.dimensions = settings.embedding.embedding_dimensions
        
        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        
        # Token encoding for accurate token counting
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Similar to embedding models
        
        self.stats = EmbeddingStats()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.encoding.encode(text))
    
    @retry(
        stop=stop_after_attempt(settings.embedding.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Includes retry logic for rate limits and transient errors.
        """
        try:
            response = await self.async_client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
            
            self.stats.api_calls += 1
            
            # Extract embeddings in correct order
            embeddings = [item.embedding for item in response.data]
            
            logger.info(
                "embedding_batch_completed",
                batch_size=len(texts),
                model=self.model,
                total_api_calls=self.stats.api_calls,
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(
                "embedding_batch_failed",
                error=str(e),
                batch_size=len(texts),
                model=self.model,
            )
            raise
    
    async def embed_chunks(
        self, 
        chunks: List[Chunk],
        document_token_count: int | None = None,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunks to embed
            document_token_count: Total token count of source document
                                 (for two-tier optimization)
        
        Returns:
            List of EmbeddingResult objects
        """
        start_time = time.time()
        
        # Two-tier optimization: skip embedding if document is small
        if (
            settings.embedding.enable_two_tier
            and document_token_count is not None
            and document_token_count < settings.embedding.small_doc_threshold
        ):
            logger.info(
                "skipping_small_document",
                token_count=document_token_count,
                threshold=settings.embedding.small_doc_threshold,
                chunks_count=len(chunks),
            )
            self.stats.skipped_small_docs += 1
            
            # For small docs, embed the entire document as single chunk
            # (This assumes caller will create a single chunk for small docs)
            if len(chunks) != 1:
                logger.warning(
                    "small_doc_multiple_chunks",
                    expected=1,
                    actual=len(chunks),
                )
        
        # Prepare texts and count tokens
        texts = [chunk.text for chunk in chunks]
        token_counts = [self.count_tokens(text) for text in texts]
        
        total_tokens = sum(token_counts)
        self.stats.add_tokens(total_tokens, self.model)
        self.stats.total_chunks += len(chunks)
        
        logger.info(
            "embedding_chunks",
            chunk_count=len(chunks),
            total_tokens=total_tokens,
            estimated_cost=f"${self.stats.estimated_cost:.6f}",
        )
        
        # Process in batches
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_chunks = chunks[i : i + self.batch_size]
            batch_token_counts = token_counts[i : i + self.batch_size]
            
            # Generate embeddings for batch
            embeddings = await self._embed_batch(batch_texts)
            
            # Create results
            for chunk, embedding, tokens in zip(
                batch_chunks, embeddings, batch_token_counts
            ):
                results.append(
                    EmbeddingResult(
                        chunk_id=f"chunk_{chunk.chunk_index}",
                        embedding=embedding,
                        token_count=tokens,
                        model=self.model,
                    )
                )
        
        elapsed = time.time() - start_time
        self.stats.processing_time_seconds += elapsed
        
        logger.info(
            "embedding_completed",
            chunk_count=len(chunks),
            elapsed_seconds=f"{elapsed:.2f}",
            total_cost=f"${self.stats.estimated_cost:.6f}",
        )
        
        return results
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text (e.g., search query).
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        embeddings = await self._embed_batch([text])
        return embeddings[0]
    
    def get_stats(self) -> EmbeddingStats:
        """Get embedding statistics"""
        return self.stats
    
    def reset_stats(self):
        """Reset embedding statistics"""
        self.stats = EmbeddingStats()
```

#### 1.3 Testing Embedding Service

```python
# tests/test_embeddings.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from semantic_search.embeddings import EmbeddingService, EmbeddingStats
from semantic_search.chunking.models import Chunk


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return MagicMock(
        data=[
            MagicMock(embedding=[0.1, 0.2, 0.3] * 512),  # 1536 dimensions
            MagicMock(embedding=[0.4, 0.5, 0.6] * 512),
        ]
    )


@pytest.mark.asyncio
async def test_embed_chunks(mock_openai_response):
    """Test embedding generation for chunks"""
    
    # Create test chunks
    chunks = [
        Chunk(
            text="Test chunk 1",
            chunk_index=0,
            start_offset=0,
            end_offset=12,
            token_count=3,
            section_path=["Test"],
        ),
        Chunk(
            text="Test chunk 2",
            chunk_index=1,
            start_offset=13,
            end_offset=25,
            token_count=3,
            section_path=["Test"],
        ),
    ]
    
    # Mock OpenAI client
    with patch("semantic_search.embeddings.service.AsyncOpenAI") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.embeddings.create.return_value = mock_openai_response
        mock_client.return_value = mock_instance
        
        # Create service
        service = EmbeddingService(api_key="test-key")
        
        # Generate embeddings
        results = await service.embed_chunks(chunks)
        
        # Assertions
        assert len(results) == 2
        assert all(len(r.embedding) == 1536 for r in results)
        assert results[0].chunk_id == "chunk_0"
        assert results[1].chunk_id == "chunk_1"
        
        # Verify API was called
        mock_instance.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_two_tier_optimization(mock_openai_response):
    """Test two-tier optimization skips small documents"""
    
    chunks = [
        Chunk(
            text="Small document",
            chunk_index=0,
            start_offset=0,
            end_offset=14,
            token_count=2,
            section_path=["Test"],
        )
    ]
    
    with patch("semantic_search.embeddings.service.AsyncOpenAI") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.embeddings.create.return_value = mock_openai_response
        mock_client.return_value = mock_instance
        
        service = EmbeddingService(api_key="test-key")
        
        # Document is below threshold (600 tokens)
        results = await service.embed_chunks(
            chunks, 
            document_token_count=500
        )
        
        # Should still embed but log the optimization
        assert len(results) == 1
        assert service.stats.skipped_small_docs == 1


def test_token_counting():
    """Test accurate token counting"""
    service = EmbeddingService(api_key="test-key")
    
    text = "This is a test document with some words."
    token_count = service.count_tokens(text)
    
    # Should be roughly 8-10 tokens
    assert 8 <= token_count <= 10


def test_cost_calculation():
    """Test cost tracking"""
    stats = EmbeddingStats()
    
    # text-embedding-3-small: $0.02 per 1M tokens
    stats.add_tokens(100_000, model="text-embedding-3-small")
    assert stats.estimated_cost == pytest.approx(0.002)
    
    stats.add_tokens(100_000, model="text-embedding-3-small")
    assert stats.estimated_cost == pytest.approx(0.004)
```

---

### Week 2: Vector Store Abstraction

#### 2.1 Abstract Base Class

```python
# src/semantic_search/storage/__init__.py

from .base import IVectorStore, SearchResult, DocumentMetadata
from .factory import get_vector_store

__all__ = [
    "IVectorStore",
    "SearchResult",
    "DocumentMetadata",
    "get_vector_store",
]
```

```python
# src/semantic_search/storage/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata for a stored document"""
    
    id: str
    user_id: str
    source_type: str  # "web", "obsidian", "telegram", etc.
    source_url: str
    title: str | None = None
    author: str | None = None
    created_at: datetime
    indexed_at: datetime
    content_hash: str  # SHA-256 hash of content
    chunk_count: int
    token_count: int


class SearchResult(BaseModel):
    """Result from vector similarity search"""
    
    document_id: str
    chunk_index: int
    score: float  # Similarity score (0-1)
    text: str  # Extracted chunk text
    start_offset: int
    end_offset: int
    section_path: List[str]
    document_metadata: DocumentMetadata


class IVectorStore(ABC):
    """
    Abstract base class for vector storage backends.
    
    Implementations must support:
    - Document storage with parent-child relationships
    - Vector similarity search
    - Update detection via content hashing
    - Efficient offset-based text extraction
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the vector store (create indexes, containers, etc.)
        
        Should be idempotent - safe to call multiple times.
        """
        pass
    
    @abstractmethod
    async def store_document(
        self,
        document_id: str,
        user_id: str,
        content: str,
        metadata: Dict[str, Any],
        chunks_with_embeddings: List[Dict[str, Any]],
    ) -> None:
        """
        Store a document with its chunks and embeddings.
        
        Args:
            document_id: Unique document identifier
            user_id: User who owns this document
            content: Full document text (stored once, no duplication)
            metadata: Document metadata (title, url, source_type, etc.)
            chunks_with_embeddings: List of dicts with:
                - chunk_index: int
                - start_offset: int
                - end_offset: int
                - embedding: List[float]
                - token_count: int
                - section_path: List[str]
        
        Implementation notes:
        - Store full text ONLY in document record
        - Store chunks with embeddings referencing parent document
        - Use offsets for text extraction (no text duplication)
        - Calculate and store content hash (SHA-256)
        """
        pass
    
    @abstractmethod
    async def document_exists(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        """
        Check if document exists for this user.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
        
        Returns:
            True if document exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_document_hash(
        self,
        document_id: str,
        user_id: str,
    ) -> Optional[str]:
        """
        Get stored content hash for document.
        
        Used for update detection - if hash matches current content,
        document hasn't changed and doesn't need re-indexing.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
        
        Returns:
            SHA-256 hash of content, or None if document not found
        """
        pass
    
    @abstractmethod
    async def get_document(
        self,
        document_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve full document with metadata.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
        
        Returns:
            Document dict with:
                - id: str
                - content: str (full text)
                - metadata: Dict
                - chunk_count: int
            Or None if not found
        """
        pass
    
    @abstractmethod
    async def vector_search(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: Query vector (1536 dimensions)
            user_id: User identifier (for filtering)
            limit: Maximum number of results
            filters: Optional metadata filters:
                - source_types: List[str]
                - from_date: datetime
                - to_date: datetime
        
        Returns:
            List of SearchResult objects, ordered by similarity (highest first)
        
        Implementation notes:
        - Search against chunk embeddings
        - Fetch parent document for text extraction
        - Extract chunk text using offsets: content[start:end]
        - Return results with similarity scores
        """
        pass
    
    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete document and all its chunks.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
        
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get storage statistics for user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Statistics dict with:
                - document_count: int
                - chunk_count: int
                - total_tokens: int
                - sources: Dict[str, int]  # source_type -> count
        """
        pass
```

#### 2.2 Cosmos DB Implementation

```python
# src/semantic_search/storage/cosmos_store.py

import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
import structlog

from ..config import settings
from .base import IVectorStore, SearchResult, DocumentMetadata

logger = structlog.get_logger()


class CosmosDBVectorStore(IVectorStore):
    """
    Cosmos DB implementation of vector store.
    
    Uses NoSQL API with vector indexing for similarity search.
    """
    
    def __init__(
        self,
        endpoint: str | None = None,
        key: str | None = None,
        database_name: str | None = None,
        container_name: str | None = None,
    ):
        self.endpoint = endpoint or settings.storage.cosmos_endpoint
        self.key = key or settings.storage.cosmos_key
        self.database_name = database_name or settings.storage.cosmos_database
        self.container_name = container_name or settings.storage.cosmos_container
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "Cosmos DB endpoint and key must be provided via config or parameters"
            )
        
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = None
        self.container = None
    
    async def initialize(self) -> None:
        """Initialize Cosmos DB database and container"""
        
        # Create database (idempotent)
        self.database = self.client.create_database_if_not_exists(
            id=self.database_name
        )
        
        logger.info("cosmos_database_ready", database=self.database_name)
        
        # Create container with vector indexing
        container_definition = {
            "id": self.container_name,
            "partitionKey": {"paths": ["/userId"], "kind": "Hash"},
            "indexingPolicy": {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [{"path": "/*"}],
                "vectorIndexes": [
                    {
                        "path": "/embedding",
                        "type": "quantizedFlat",  # Efficient vector index
                    }
                ],
            },
        }
        
        self.container = self.database.create_container_if_not_exists(
            id=container_definition["id"],
            partition_key=PartitionKey(path="/userId"),
            indexing_policy=container_definition["indexingPolicy"],
        )
        
        logger.info("cosmos_container_ready", container=self.container_name)
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def store_document(
        self,
        document_id: str,
        user_id: str,
        content: str,
        metadata: Dict[str, Any],
        chunks_with_embeddings: List[Dict[str, Any]],
    ) -> None:
        """Store document and chunks in Cosmos DB"""
        
        content_hash = self._compute_hash(content)
        
        # 1. Store document (full text, NO embedding)
        document_item = {
            "id": document_id,
            "type": "document",
            "userId": user_id,
            "content": {
                "fullText": content,
                "hash": content_hash,
            },
            "metadata": {
                **metadata,
                "indexedAt": datetime.utcnow().isoformat(),
            },
            "statistics": {
                "chunkCount": len(chunks_with_embeddings),
                "characterCount": len(content),
            },
        }
        
        self.container.upsert_item(document_item)
        
        logger.info(
            "document_stored",
            document_id=document_id,
            chunk_count=len(chunks_with_embeddings),
            hash=content_hash[:8],
        )
        
        # 2. Store chunks with embeddings
        for chunk_data in chunks_with_embeddings:
            chunk_item = {
                "id": f"{document_id}_chunk_{chunk_data['chunk_index']}",
                "type": "chunk",
                "userId": user_id,
                "parentDocId": document_id,
                "chunkIndex": chunk_data["chunk_index"],
                "position": {
                    "startOffset": chunk_data["start_offset"],
                    "endOffset": chunk_data["end_offset"],
                },
                "embedding": chunk_data["embedding"],
                "metadata": {
                    "sectionPath": chunk_data.get("section_path", []),
                    "tokenCount": chunk_data.get("token_count", 0),
                },
            }
            
            self.container.upsert_item(chunk_item)
        
        logger.info(
            "chunks_stored",
            document_id=document_id,
            chunk_count=len(chunks_with_embeddings),
        )
    
    async def document_exists(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        """Check if document exists"""
        
        query = """
            SELECT VALUE COUNT(1)
            FROM c
            WHERE c.id = @document_id
              AND c.userId = @user_id
              AND c.type = 'document'
        """
        
        items = list(
            self.container.query_items(
                query=query,
                parameters=[
                    {"name": "@document_id", "value": document_id},
                    {"name": "@user_id", "value": user_id},
                ],
                enable_cross_partition_query=False,
                partition_key=user_id,
            )
        )
        
        return items[0] > 0 if items else False
    
    async def get_document_hash(
        self,
        document_id: str,
        user_id: str,
    ) -> Optional[str]:
        """Get document content hash"""
        
        query = """
            SELECT c.content.hash
            FROM c
            WHERE c.id = @document_id
              AND c.userId = @user_id
              AND c.type = 'document'
        """
        
        items = list(
            self.container.query_items(
                query=query,
                parameters=[
                    {"name": "@document_id", "value": document_id},
                    {"name": "@user_id", "value": user_id},
                ],
                enable_cross_partition_query=False,
                partition_key=user_id,
            )
        )
        
        return items[0]["hash"] if items else None
    
    async def get_document(
        self,
        document_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve full document"""
        
        try:
            item = self.container.read_item(
                item=document_id,
                partition_key=user_id,
            )
            
            if item.get("type") != "document":
                return None
            
            return {
                "id": item["id"],
                "content": item["content"]["fullText"],
                "metadata": item.get("metadata", {}),
                "chunk_count": item.get("statistics", {}).get("chunkCount", 0),
            }
        
        except CosmosResourceNotFoundError:
            return None
    
    async def vector_search(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform vector similarity search"""
        
        # Build query with vector similarity
        query = """
            SELECT
                c.parentDocId,
                c.chunkIndex,
                c.position,
                c.metadata,
                VectorDistance(c.embedding, @queryEmbedding) AS score
            FROM c
            WHERE c.type = 'chunk'
              AND c.userId = @userId
        """
        
        parameters = [
            {"name": "@queryEmbedding", "value": query_embedding},
            {"name": "@userId", "value": user_id},
        ]
        
        # Add metadata filters if provided
        if filters:
            if "source_types" in filters:
                # This requires joining with parent document - simplified for now
                pass
        
        query += """
            ORDER BY VectorDistance(c.embedding, @queryEmbedding)
            OFFSET 0 LIMIT @limit
        """
        
        parameters.append({"name": "@limit", "value": limit})
        
        # Execute search
        chunk_results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=False,
                partition_key=user_id,
            )
        )
        
        # Fetch parent documents and extract text
        search_results = []
        
        for chunk in chunk_results:
            # Get parent document
            doc = await self.get_document(chunk["parentDocId"], user_id)
            
            if not doc:
                continue
            
            # Extract chunk text using offsets
            chunk_text = doc["content"][
                chunk["position"]["startOffset"] : chunk["position"]["endOffset"]
            ]
            
            # Create search result
            search_results.append(
                SearchResult(
                    document_id=chunk["parentDocId"],
                    chunk_index=chunk["chunkIndex"],
                    score=chunk["score"],
                    text=chunk_text,
                    start_offset=chunk["position"]["startOffset"],
                    end_offset=chunk["position"]["endOffset"],
                    section_path=chunk["metadata"].get("sectionPath", []),
                    document_metadata=DocumentMetadata(
                        id=doc["id"],
                        user_id=user_id,
                        **doc["metadata"],
                        chunk_count=doc["chunk_count"],
                        token_count=0,  # TODO: Store this
                    ),
                )
            )
        
        logger.info(
            "vector_search_completed",
            results_count=len(search_results),
            limit=limit,
        )
        
        return search_results
    
    async def delete_document(
        self,
        document_id: str,
        user_id: str,
    ) -> bool:
        """Delete document and its chunks"""
        
        try:
            # Delete document
            self.container.delete_item(
                item=document_id,
                partition_key=user_id,
            )
            
            # Delete all chunks
            query = """
                SELECT c.id
                FROM c
                WHERE c.parentDocId = @document_id
                  AND c.type = 'chunk'
                  AND c.userId = @user_id
            """
            
            chunk_ids = [
                item["id"]
                for item in self.container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@document_id", "value": document_id},
                        {"name": "@user_id", "value": user_id},
                    ],
                    enable_cross_partition_query=False,
                    partition_key=user_id,
                )
            ]
            
            for chunk_id in chunk_ids:
                self.container.delete_item(
                    item=chunk_id,
                    partition_key=user_id,
                )
            
            logger.info(
                "document_deleted",
                document_id=document_id,
                chunks_deleted=len(chunk_ids),
            )
            
            return True
        
        except CosmosResourceNotFoundError:
            return False
    
    async def get_stats(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get storage statistics"""
        
        # Count documents
        doc_query = """
            SELECT VALUE COUNT(1)
            FROM c
            WHERE c.type = 'document'
              AND c.userId = @user_id
        """
        
        doc_count = list(
            self.container.query_items(
                query=doc_query,
                parameters=[{"name": "@user_id", "value": user_id}],
                enable_cross_partition_query=False,
                partition_key=user_id,
            )
        )[0]
        
        # Count chunks
        chunk_query = """
            SELECT VALUE COUNT(1)
            FROM c
            WHERE c.type = 'chunk'
              AND c.userId = @user_id
        """
        
        chunk_count = list(
            self.container.query_items(
                query=chunk_query,
                parameters=[{"name": "@user_id", "value": user_id}],
                enable_cross_partition_query=False,
                partition_key=user_id,
            )
        )[0]
        
        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "total_tokens": 0,  # TODO: Aggregate from metadata
            "sources": {},  # TODO: Group by source_type
        }
```

#### 2.3 Factory Pattern

```python
# src/semantic_search/storage/factory.py

from ..config import settings
from .base import IVectorStore


def get_vector_store() -> IVectorStore:
    """
    Factory function to create vector store based on configuration.
    
    Returns:
        Configured IVectorStore implementation
    
    Raises:
        ValueError: If provider is unknown or not configured
    """
    
    provider = settings.storage.provider
    
    if provider == "cosmos":
        from .cosmos_store import CosmosDBVectorStore
        
        return CosmosDBVectorStore()
    
    elif provider == "pinecone":
        from .pinecone_store import PineconeVectorStore
        
        return PineconeVectorStore()
    
    elif provider == "weaviate":
        from .weaviate_store import WeaviateVectorStore
        
        return WeaviateVectorStore()
    
    elif provider == "local":
        from .local_store import LocalVectorStore
        
        return LocalVectorStore()
    
    else:
        raise ValueError(
            f"Unknown vector store provider: {provider}. "
            f"Supported: cosmos, pinecone, weaviate, local"
        )
```

---

### Week 3: Complete Ingestion Pipeline

#### 3.1 Pipeline Orchestrator

```python
# src/semantic_search/pipeline/__init__.py

from .orchestrator import IngestionPipeline, IngestionResult

__all__ = ["IngestionPipeline", "IngestionResult"]
```

```python
# src/semantic_search/pipeline/orchestrator.py

import hashlib
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import structlog

from ..models import RawDocument, Document
from ..processors import WebPageProcessor, MarkdownProcessor
from ..chunking import MarkdownChunker
from ..embeddings import EmbeddingService
from ..storage import IVectorStore, get_vector_store
from ..config import settings

logger = structlog.get_logger()


class IngestionResult(BaseModel):
    """Result of ingestion pipeline"""
    
    document_id: str
    status: str  # "indexed", "updated", "skipped"
    reason: Optional[str] = None
    chunk_count: int = 0
    token_count: int = 0
    estimated_cost: float = 0.0
    processing_time_seconds: float = 0.0


class IngestionPipeline:
    """
    Complete ingestion pipeline: Load → Process → Chunk → Embed → Store
    
    Features:
    - Update detection via content hashing
    - Two-tier embedding optimization
    - Configurable storage backend
    - Comprehensive logging
    """
    
    def __init__(
        self,
        vector_store: Optional[IVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        enable_embedding: bool = True,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = (
            embedding_service if enable_embedding else None
        )
        self.enable_embedding = enable_embedding
        
        # Processors
        self.web_processor = WebPageProcessor(include_enrichment=True)
        self.md_processor = MarkdownProcessor(include_enrichment=True)
        
        # Chunker
        self.chunker = MarkdownChunker(
            token_threshold=settings.embedding.small_doc_threshold,
        )
    
    async def initialize(self):
        """Initialize pipeline (create storage indexes, etc.)"""
        await self.vector_store.initialize()
        logger.info("pipeline_initialized")
    
    def _generate_document_id(self, raw_doc: RawDocument) -> str:
        """
        Generate unique document ID from source.
        
        For URLs: hash of normalized URL
        For files: hash of file path
        """
        if raw_doc.url:
            # Normalize URL (remove trailing slash, query params, etc.)
            normalized = raw_doc.url.lower().rstrip("/").split("?")[0]
            return f"doc_{hashlib.md5(normalized.encode()).hexdigest()}"
        elif raw_doc.file_path:
            return f"doc_{hashlib.md5(raw_doc.file_path.encode()).hexdigest()}"
        else:
            raise ValueError("RawDocument must have url or file_path")
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def ingest(
        self,
        raw_doc: RawDocument,
        user_id: str | None = None,
    ) -> IngestionResult:
        """
        Execute complete ingestion pipeline.
        
        Args:
            raw_doc: Raw document to ingest
            user_id: User identifier (defaults to config)
        
        Returns:
            IngestionResult with status and statistics
        """
        import time
        
        start_time = time.time()
        user_id = user_id or settings.storage.user_id
        
        # 1. Generate document ID
        document_id = self._generate_document_id(raw_doc)
        
        logger.info(
            "ingestion_started",
            document_id=document_id,
            source_type=raw_doc.source_type,
            url=raw_doc.url,
        )
        
        # 2. Process document
        if raw_doc.source_type == "web":
            document = self.web_processor.process(raw_doc)
        elif raw_doc.source_type in ["markdown", "obsidian"]:
            document = self.md_processor.process(raw_doc)
        else:
            raise ValueError(f"Unsupported source type: {raw_doc.source_type}")
        
        # 3. Check if document needs updating (hash comparison)
        content_hash = self._compute_content_hash(document.content)
        existing_hash = await self.vector_store.get_document_hash(
            document_id, user_id
        )
        
        if existing_hash == content_hash:
            elapsed = time.time() - start_time
            logger.info(
                "document_unchanged",
                document_id=document_id,
                hash=content_hash[:8],
            )
            return IngestionResult(
                document_id=document_id,
                status="skipped",
                reason="Content unchanged (hash match)",
                processing_time_seconds=elapsed,
            )
        
        # 4. Chunk document
        chunks = self.chunker.chunk_document(document.content)
        
        logger.info(
            "document_chunked",
            document_id=document_id,
            chunk_count=len(chunks),
        )
        
        # 5. Generate embeddings (if enabled)
        chunks_with_embeddings = []
        estimated_cost = 0.0
        
        if self.enable_embedding and self.embedding_service:
            # Calculate total document token count
            doc_token_count = sum(chunk.token_count for chunk in chunks)
            
            # Embed chunks
            embedding_results = await self.embedding_service.embed_chunks(
                chunks,
                document_token_count=doc_token_count,
            )
            
            # Combine chunks with embeddings
            for chunk, embedding_result in zip(chunks, embedding_results):
                chunks_with_embeddings.append(
                    {
                        "chunk_index": chunk.chunk_index,
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset,
                        "embedding": embedding_result.embedding,
                        "token_count": embedding_result.token_count,
                        "section_path": chunk.section_path,
                    }
                )
            
            stats = self.embedding_service.get_stats()
            estimated_cost = stats.estimated_cost
        
        else:
            # No embedding - just store chunks without vectors
            for chunk in chunks:
                chunks_with_embeddings.append(
                    {
                        "chunk_index": chunk.chunk_index,
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset,
                        "embedding": [],  # Empty embedding
                        "token_count": chunk.token_count,
                        "section_path": chunk.section_path,
                    }
                )
        
        # 6. Store in vector database
        metadata = {
            "source_type": raw_doc.source_type,
            "source_url": raw_doc.url or raw_doc.file_path,
            "title": document.title,
            "author": document.metadata.get("author"),
            "created_at": datetime.utcnow().isoformat(),
            "content_hash": content_hash,
        }
        
        await self.vector_store.store_document(
            document_id=document_id,
            user_id=user_id,
            content=document.content,
            metadata=metadata,
            chunks_with_embeddings=chunks_with_embeddings,
        )
        
        # 7. Return result
        elapsed = time.time() - start_time
        status = "updated" if existing_hash else "indexed"
        
        logger.info(
            "ingestion_completed",
            document_id=document_id,
            status=status,
            chunk_count=len(chunks),
            cost=f"${estimated_cost:.6f}",
            elapsed=f"{elapsed:.2f}s",
        )
        
        return IngestionResult(
            document_id=document_id,
            status=status,
            chunk_count=len(chunks),
            token_count=sum(c["token_count"] for c in chunks_with_embeddings),
            estimated_cost=estimated_cost,
            processing_time_seconds=elapsed,
        )
```

#### 3.2 CLI (Already Implemented)

The Typer-based ingestion CLI is already implemented in the repository (see `src/semantic_search/cli.py`).

Once embeddings + storage land, extend the CLI with `--embed/--store` and add `search`/`stats` commands.

---

### Week 4: Testing & Documentation

#### 4.1 Integration Tests

```python
# tests/test_integration.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from semantic_search.pipeline import IngestionPipeline, IngestionResult
from semantic_search.models import RawDocument


@pytest.mark.asyncio
async def test_complete_pipeline():
    """Test complete ingestion pipeline end-to-end"""
    
    # Create mock vector store
    mock_store = AsyncMock()
    mock_store.get_document_hash.return_value = None  # Document doesn't exist
    mock_store.initialize.return_value = None
    mock_store.store_document.return_value = None
    
    # Create mock embedding service
    mock_embedder = AsyncMock()
    mock_embedder.embed_chunks.return_value = [
        MagicMock(
            chunk_id="chunk_0",
            embedding=[0.1] * 1536,
            token_count=100,
            model="text-embedding-3-small",
        )
    ]
    mock_embedder.get_stats.return_value = MagicMock(estimated_cost=0.001)
    
    # Create pipeline
    pipeline = IngestionPipeline(
        vector_store=mock_store,
        embedding_service=mock_embedder,
        enable_embedding=True,
    )
    
    await pipeline.initialize()
    
    # Create test document
    raw_doc = RawDocument(
        content="# Test Document\n\nThis is a test.",
        source_type="markdown",
        file_path="/test/doc.md",
    )
    
    # Run pipeline
    result = await pipeline.ingest(raw_doc, user_id="test-user")
    
    # Assertions
    assert result.status == "indexed"
    assert result.chunk_count > 0
    assert result.estimated_cost > 0
    
    # Verify store was called
    mock_store.store_document.assert_called_once()


@pytest.mark.asyncio
async def test_update_detection():
    """Test that unchanged documents are skipped"""
    
    mock_store = AsyncMock()
    mock_store.get_document_hash.return_value = (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )  # Hash of empty string
    
    pipeline = IngestionPipeline(
        vector_store=mock_store,
        enable_embedding=False,
    )
    
    raw_doc = RawDocument(
        content="",  # Will produce same hash
        source_type="markdown",
        file_path="/test/doc.md",
    )
    
    result = await pipeline.ingest(raw_doc, user_id="test-user")
    
    assert result.status == "skipped"
    assert "hash match" in result.reason.lower()
```

#### 4.2 Documentation

Create comprehensive documentation:

**1. `docs/embedding-guide.md`** - Embedding service usage and cost optimization
**2. `docs/storage-providers.md`** - Comparison of Cosmos DB vs Pinecone vs Weaviate
**3. `docs/pipeline-guide.md`** - Complete pipeline usage with examples
**4. Update `README.md`** - Add pipeline examples and quick start

---

## 📊 Success Metrics

Track these metrics to validate implementation:

### Functional Metrics

- [ ] Documents ingested successfully (>95% success rate)
- [ ] Hash-based update detection working (unchanged docs skipped)
- [ ] Embeddings generated with correct dimensions (1536)
- [ ] Vector search returns relevant results (score >0.5 for good matches)
- [ ] Offset-based text extraction accurate (no corruption)

### Performance Metrics

- [ ] Embedding generation: <5s per document (typical web article)
- [ ] Storage write: <1s per document + chunks
- [ ] Vector search: <500ms for p95
- [ ] Two-tier optimization: >70% embedding cost savings on short content

### Cost Metrics

- [ ] Embedding cost: ~$0.02 per 1000 documents (4000 chars each)
- [ ] Cosmos DB: $0/month (free tier)
- [ ] Total: <$5/month for 1000 docs

---

## 🔧 Development Workflow

### Daily Development Routine

1. **Pull latest changes**
   ```bash
   git pull origin main
   ```

2. **Activate environment**
   ```bash
   .venv\Scripts\activate
   ```

3. **Run tests**
   ```bash
   pytest -v
   ```

4. **Format code**
   ```bash
   black src/ tests/
   ruff check src/ tests/ --fix
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: implement embedding service"
   git push origin feature/embeddings
   ```

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/embeddings` - Embedding service implementation
- `feature/cosmos-db` - Cosmos DB storage implementation
- `feature/pipeline` - Pipeline orchestrator

---

## 🚀 Deployment Checklist

Before deploying to production:

### Environment Setup

- [ ] Create `.env` file with all required keys
- [ ] Set up Azure Cosmos DB account (free tier)
- [ ] Create Cosmos DB database and container
- [ ] Enable vector indexing on `/embedding` path
- [ ] Test connection with `ingestion-cli stats`

### Security

- [ ] Store API keys in Azure Key Vault (production)
- [ ] Enable Managed Identity for Azure Functions
- [ ] Rotate OpenAI API key regularly
- [ ] Set up monitoring and alerts

### Testing

- [ ] Run full test suite: `pytest`
- [ ] Test with real URLs: `ingestion-cli https://example.com --embed --store`
- [ ] Validate search: `ingestion-cli search "test query"`
- [ ] Check statistics: `ingestion-cli stats`

---

## 📝 Next Steps After Completion

Once Phase 1 is complete, proceed with:

### Phase 2: Additional Source Connectors (Weeks 5-8)

1. **Obsidian Connector** - Index local markdown files
2. **Telegram Connector** - Fetch channel messages
3. **Email Connector** - Index Gmail messages
4. **PDF Connector** - Extract and index PDF documents

### Phase 3: Search API (.NET) (Weeks 9-12)

Build REST API for:
- Semantic search endpoint
- Document retrieval
- Statistics and analytics
- User management

### Phase 4: Frontend (Weeks 13-16)

Create React SPA with:
- Search interface
- Result visualization
- Filters and sorting
- Document viewer

---

## 🎯 Summary

This plan provides a complete, production-ready implementation for:

✅ **Embedding generation** with cost optimization  
✅ **Provider-agnostic storage** (easily swap Cosmos ↔ Pinecone ↔ Weaviate)  
✅ **End-to-end pipeline** from URL to searchable chunks  
✅ **Update detection** to avoid re-indexing  
✅ **Comprehensive testing** and documentation

**Estimated completion:** 4-6 weeks of focused development

Good luck with the implementation! 🚀
