# Phase 1 Implementation Plan: Embeddings, Storage & Complete Pipeline (with LangChain)

**Project:** Semantic Search Engine  
**Phase:** 1 - Core Indexing Infrastructure  
**Duration:** 4-6 weeks  
**Status:** Ready to implement  
**Created:** January 2026  
**Version:** 2.0 - LangChain Integrated

---

## 📋 Executive Summary

This plan completes Phase 1 by implementing:

1. **LangChain-Based Embedding Generation** - Provider-agnostic with OpenAI as default
2. **Vector Store Abstraction** - Swappable storage backends (Cosmos DB, Pinecone, Weaviate)
3. **Complete Ingestion Pipeline** - End-to-end document indexing
4. **Update Detection** - Hash-based change tracking
5. **Foundation for Phase 2** - Ready for summarization and tag extraction chains

**Key Architectural Principles:**

- **LangChain First** - All AI operations use LangChain abstractions
- **Provider Agnostic** - Easy to swap OpenAI → Cohere → Hugging Face
- **Learning by Doing** - Hands-on with LCEL (LangChain Expression Language)
- **Future Ready** - Prepared for RAG, summarization, and Q&A in Phase 2

---

## 🎯 Success Criteria

By the end of this implementation, you will have:

- [ ] LangChain integrated for all AI operations
- [ ] Documents indexed with embeddings stored in vector database
- [ ] Semantic search returning relevant results
- [ ] Hash-based update detection working (no re-indexing unchanged docs)
- [ ] CLI supporting full pipeline: `ingestion-cli <url> --embed --store`
- [ ] Embedding provider can be swapped via configuration
- [ ] Storage provider can be swapped via configuration
- [ ] Cost tracking for embedding API calls
- [ ] >80% test coverage for new code
- [ ] **Understanding of LangChain core concepts** (chains, runnables, providers)

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
│  │         LANGCHAIN EMBEDDING SERVICE                     │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  Embedding Provider Abstraction                  │  │   │
│  │  ├──────────────────────────────────────────────────┤  │   │
│  │  │  • OpenAIEmbeddings (default)                   │  │   │
│  │  │  • CohereEmbeddings (alternative)               │  │   │
│  │  │  • HuggingFaceEmbeddings (local)                │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  Features:                                               │   │
│  │  • Batch processing (up to 2048 texts)                  │   │
│  │  • Cost tracking & logging                              │   │
│  │  • Automatic retry logic                                │   │
│  │  • Two-tier optimization (skip <600 token docs)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │    VECTOR STORE ABSTRACTION (Repository Pattern)       │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  IVectorStore (Abstract Base Class)             │  │   │
│  │  ├──────────────────────────────────────────────────┤  │   │
│  │  │  + store_document(doc, chunks_with_embeddings)  │  │   │
│  │  │  + get_document(doc_id) -> Document             │  │   │
│  │  │  + vector_search(embedding, limit) -> Results   │  │   │
│  │  │  + document_exists(doc_id) -> bool              │  │   │
│  │  │  + update_document(doc_id, updates)             │  │   │
│  │  │  + delete_document(doc_id)                      │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  │                          │                              │   │
│  │          ┌───────────────┼───────────────┐             │   │
│  │          ▼               ▼               ▼             │   │
│  │    ┌──────────┐    ┌──────────┐    ┌──────────┐       │   │
│  │    │ Cosmos   │    │ Pinecone │    │ Weaviate │       │   │
│  │    │ DB Store │    │  Store   │    │  Store   │       │   │
│  │    └──────────┘    └──────────┘    └──────────┘       │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │      FUTURE: LANGCHAIN LLM CHAINS (Phase 2)            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • Summarization Chain (Claude)                         │   │
│  │  • Tag Extraction Chain (Structured Output)             │   │
│  │  • Q&A Chain (RAG)                                      │   │
│  │  • Multi-document Summarization                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎓 LangChain Learning Objectives

As you implement this phase, you'll gain hands-on experience with:

### Core LangChain Concepts

1. **Runnables** - Base abstraction for all LangChain components
2. **Embeddings** - Text-to-vector transformation
3. **Provider Abstraction** - Swap OpenAI ↔ Cohere ↔ Hugging Face
4. **Error Handling** - Built-in retry logic and graceful failures
5. **Cost Tracking** - Token counting and usage monitoring

### LCEL (LangChain Expression Language)

You'll learn the foundation for Phase 2:
- Chaining components with `|` operator
- Prompt templates and output parsers
- Async/streaming support

### Preparation for Phase 2

This implementation sets you up for:
- **Summarization chains**: `prompt | llm | output_parser`
- **Structured output**: Using Pydantic models with LLMs
- **RAG patterns**: Retrieval + generation workflows

---

## 📦 Implementation Plan

### Week 1: LangChain Embedding Service

#### 1.1 Dependencies & Configuration

**Update `pyproject.toml`:**

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    
    # LangChain core
    "langchain>=0.1.0",
    "langchain-core>=0.1.0",
    
    # LangChain integrations
    "langchain-openai>=0.0.5",
    "langchain-anthropic>=0.1.0",  # For Phase 2 summarization
    "langchain-community>=0.0.20",
    
    # Supporting libraries
    "tiktoken>=0.5.0",
    "tenacity>=8.0.0",
]

[project.optional-dependencies]
# Vector store providers
cosmos = [
    "azure-cosmos>=4.5.0",
    "azure-identity>=1.15.0",
]
pinecone = [
    "pinecone-client>=3.0.0",
]
weaviate = [
    "weaviate-client>=4.0.0",
]

# Alternative embedding providers
cohere = [
    "langchain-cohere>=0.0.1",
    "cohere>=4.0.0",
]
huggingface = [
    "langchain-huggingface>=0.0.1",
    "sentence-transformers>=2.2.0",
]

dev = [
    # ... existing dev dependencies ...
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
]
```

**Create configuration file:**

```python
# src/semantic_search/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class EmbeddingConfig(BaseSettings):
    """Embedding service configuration"""
    
    # Provider selection
    provider: Literal["openai", "cohere", "huggingface"] = Field(
        "openai",
        env="EMBEDDING_PROVIDER"
    )
    
    # OpenAI settings
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_dimensions: int = Field(1536, env="OPENAI_EMBEDDING_DIMENSIONS")
    
    # Cohere settings (alternative)
    cohere_api_key: str | None = Field(None, env="COHERE_API_KEY")
    cohere_model: str = Field("embed-english-v3.0", env="COHERE_EMBEDDING_MODEL")
    
    # Hugging Face settings (local embeddings)
    huggingface_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        env="HUGGINGFACE_EMBEDDING_MODEL"
    )
    
    # Common settings
    batch_size: int = Field(100, env="EMBEDDING_BATCH_SIZE")
    max_retries: int = Field(3, env="EMBEDDING_MAX_RETRIES")
    
    # Two-tier optimization
    enable_two_tier: bool = Field(True, env="ENABLE_TWO_TIER_EMBEDDING")
    small_doc_threshold: int = Field(600, env="SMALL_DOC_THRESHOLD")


class LLMConfig(BaseSettings):
    """LLM configuration for Phase 2 (summarization, tags)"""
    
    # Provider selection
    provider: Literal["anthropic", "openai"] = Field(
        "anthropic",
        env="LLM_PROVIDER"
    )
    
    # Anthropic settings
    anthropic_api_key: str | None = Field(None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-sonnet-4", env="ANTHROPIC_MODEL")
    
    # OpenAI settings
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo-preview", env="OPENAI_LLM_MODEL")
    
    # Common settings
    temperature: float = Field(0.0, env="LLM_TEMPERATURE")
    max_tokens: int = Field(1000, env="LLM_MAX_TOKENS")


class StorageConfig(BaseSettings):
    """Vector store configuration"""
    
    provider: Literal["cosmos", "pinecone", "weaviate", "local"] = Field(
        "cosmos", 
        env="VECTOR_STORE_PROVIDER"
    )
    user_id: str = Field("vasyl", env="USER_ID")
    
    # Cosmos DB specific
    cosmos_endpoint: str | None = Field(None, env="COSMOS_ENDPOINT")
    cosmos_key: str | None = Field(None, env="COSMOS_KEY")
    cosmos_database: str = Field("semantic-search", env="COSMOS_DATABASE")
    cosmos_container: str = Field("documents-and-chunks", env="COSMOS_CONTAINER")
    
    # Pinecone specific
    pinecone_api_key: str | None = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: str | None = Field(None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("semantic-search", env="PINECONE_INDEX_NAME")
    
    # Weaviate specific
    weaviate_url: str | None = Field(None, env="WEAVIATE_URL")
    weaviate_api_key: str | None = Field(None, env="WEAVIATE_API_KEY")
    weaviate_class_name: str = Field("Document", env="WEAVIATE_CLASS_NAME")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class Settings(BaseSettings):
    """Global application settings"""
    
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    storage: StorageConfig = StorageConfig()
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or text


# Global settings instance
settings = Settings()
```

**Create `.env.template`:**

```bash
# .env.template - Copy to .env and fill in your values

# ============================================================================
# EMBEDDING CONFIGURATION
# ============================================================================

# Provider: openai | cohere | huggingface
EMBEDDING_PROVIDER=openai

# OpenAI Settings (if using OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

# Cohere Settings (if using Cohere)
# COHERE_API_KEY=your-key
# COHERE_EMBEDDING_MODEL=embed-english-v3.0

# Hugging Face Settings (if using local embeddings)
# HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Common Settings
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_RETRIES=3
ENABLE_TWO_TIER_EMBEDDING=true
SMALL_DOC_THRESHOLD=600

# ============================================================================
# LLM CONFIGURATION (Phase 2)
# ============================================================================

# Provider: anthropic | openai
LLM_PROVIDER=anthropic

# Anthropic Settings (Claude)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4

# OpenAI Settings (GPT)
# OPENAI_LLM_MODEL=gpt-4-turbo-preview

# Common Settings
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1000

# ============================================================================
# VECTOR STORE CONFIGURATION
# ============================================================================

# Provider: cosmos | pinecone | weaviate | local
VECTOR_STORE_PROVIDER=cosmos
USER_ID=vasyl

# Cosmos DB Configuration
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-key-here
COSMOS_DATABASE=semantic-search
COSMOS_CONTAINER=documents-and-chunks

# Pinecone Configuration (if using Pinecone)
# PINECONE_API_KEY=your-key-here
# PINECONE_ENVIRONMENT=us-east-1-aws
# PINECONE_INDEX_NAME=semantic-search

# Weaviate Configuration (if using Weaviate)
# WEAVIATE_URL=http://localhost:8080
# WEAVIATE_API_KEY=your-key-here
# WEAVIATE_CLASS_NAME=Document

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### 1.2 LangChain Embedding Service Implementation

**Create embedding service with provider abstraction:**

```python
# src/semantic_search/embeddings/__init__.py

from .service import EmbeddingService, EmbeddingResult
from .models import EmbeddingStats
from .providers import get_embedding_provider

__all__ = [
    "EmbeddingService",
    "EmbeddingResult",
    "EmbeddingStats",
    "get_embedding_provider",
]
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
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def add_tokens(self, tokens: int):
        """Add tokens and calculate cost based on provider"""
        self.total_tokens += tokens
        
        # Pricing per 1M tokens (as of Jan 2025)
        pricing = {
            # OpenAI
            "text-embedding-3-small": 0.02,
            "text-embedding-3-large": 0.13,
            "text-embedding-ada-002": 0.10,
            # Cohere
            "embed-english-v3.0": 0.10,
            "embed-multilingual-v3.0": 0.10,
            # Hugging Face (local - free)
            "sentence-transformers": 0.0,
        }
        
        cost_per_million = pricing.get(self.model, 0.02)
        self.estimated_cost = (self.total_tokens / 1_000_000) * cost_per_million


class EmbeddingResult(BaseModel):
    """Result from embedding operation"""
    
    chunk_id: str
    embedding: list[float]
    token_count: int
    model: str
    provider: str
```

```python
# src/semantic_search/embeddings/providers.py

from typing import Protocol
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
import structlog

from ..config import settings

logger = structlog.get_logger()


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers"""
    
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents"""
        ...
    
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query"""
        ...


def get_embedding_provider() -> Embeddings:
    """
    Factory function to create embedding provider based on configuration.
    
    Returns:
        LangChain Embeddings implementation
    
    Raises:
        ValueError: If provider is unknown or not configured
    """
    
    provider = settings.embedding.provider
    
    if provider == "openai":
        if not settings.embedding.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        
        logger.info(
            "initializing_embedding_provider",
            provider="openai",
            model=settings.embedding.openai_model,
            dimensions=settings.embedding.openai_dimensions,
        )
        
        return OpenAIEmbeddings(
            openai_api_key=settings.embedding.openai_api_key,
            model=settings.embedding.openai_model,
            dimensions=settings.embedding.openai_dimensions,
            # LangChain handles retries automatically
            max_retries=settings.embedding.max_retries,
        )
    
    elif provider == "cohere":
        try:
            from langchain_cohere import CohereEmbeddings
        except ImportError:
            raise ImportError(
                "Cohere embeddings require: pip install langchain-cohere cohere"
            )
        
        if not settings.embedding.cohere_api_key:
            raise ValueError("COHERE_API_KEY is required for Cohere embeddings")
        
        logger.info(
            "initializing_embedding_provider",
            provider="cohere",
            model=settings.embedding.cohere_model,
        )
        
        return CohereEmbeddings(
            cohere_api_key=settings.embedding.cohere_api_key,
            model=settings.embedding.cohere_model,
        )
    
    elif provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "Hugging Face embeddings require: "
                "pip install langchain-huggingface sentence-transformers"
            )
        
        logger.info(
            "initializing_embedding_provider",
            provider="huggingface",
            model=settings.embedding.huggingface_model,
        )
        
        return HuggingFaceEmbeddings(
            model_name=settings.embedding.huggingface_model,
        )
    
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            f"Supported: openai, cohere, huggingface"
        )
```

```python
# src/semantic_search/embeddings/service.py

import asyncio
import time
from typing import List
import tiktoken
import structlog

from langchain_core.embeddings import Embeddings

from ..config import settings
from ..chunking.models import Chunk
from .models import EmbeddingStats, EmbeddingResult
from .providers import get_embedding_provider

logger = structlog.get_logger()


class EmbeddingService:
    """
    LangChain-based service for generating embeddings.
    
    Features:
    - Provider-agnostic (OpenAI, Cohere, Hugging Face)
    - Batch processing for efficiency
    - Two-tier optimization (skip small docs)
    - Automatic retry on rate limits (via LangChain)
    - Cost tracking
    
    Learning Notes:
    - Uses LangChain's Embeddings abstraction
    - Demonstrates provider swapping via configuration
    - Prepares for Phase 2 LLM chains
    """
    
    def __init__(
        self,
        embedding_provider: Embeddings | None = None,
        batch_size: int | None = None,
    ):
        # Use provided embedder or get from config
        self.embedder = embedding_provider or get_embedding_provider()
        self.batch_size = batch_size or settings.embedding.batch_size
        
        # Token encoding for accurate token counting
        # Note: This is approximate for non-OpenAI models
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
        # Track statistics
        self.stats = EmbeddingStats(
            provider=settings.embedding.provider,
            model=self._get_model_name(),
        )
    
    def _get_model_name(self) -> str:
        """Get model name from configuration"""
        if settings.embedding.provider == "openai":
            return settings.embedding.openai_model
        elif settings.embedding.provider == "cohere":
            return settings.embedding.cohere_model
        elif settings.embedding.provider == "huggingface":
            return settings.embedding.huggingface_model
        return "unknown"
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Note: This is approximate for non-OpenAI models.
        """
        return len(self.encoding.encode(text))
    
    async def embed_chunks(
        self, 
        chunks: List[Chunk],
        document_token_count: int | None = None,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for document chunks using LangChain.
        
        Args:
            chunks: List of chunks to embed
            document_token_count: Total token count of source document
                                 (for two-tier optimization)
        
        Returns:
            List of EmbeddingResult objects
        
        Learning Notes:
        - Uses LangChain's async embed_documents() method
        - Demonstrates batch processing
        - Shows how to track costs across providers
        """
        start_time = time.time()
        
        # Two-tier optimization: skip embedding if document is small
        if (
            settings.embedding.enable_two_tier
            and document_token_count is not None
            and document_token_count < settings.embedding.small_doc_threshold
        ):
            logger.info(
                "small_document_optimization",
                token_count=document_token_count,
                threshold=settings.embedding.small_doc_threshold,
                chunks_count=len(chunks),
                note="Document fits in single chunk - optimal for cost",
            )
            self.stats.skipped_small_docs += 1
        
        # Prepare texts and count tokens
        texts = [chunk.text for chunk in chunks]
        token_counts = [self.count_tokens(text) for text in texts]
        
        total_tokens = sum(token_counts)
        self.stats.add_tokens(total_tokens)
        self.stats.total_chunks += len(chunks)
        
        logger.info(
            "embedding_chunks",
            provider=settings.embedding.provider,
            model=self.stats.model,
            chunk_count=len(chunks),
            total_tokens=total_tokens,
            estimated_cost=f"${self.stats.estimated_cost:.6f}",
        )
        
        # Process in batches using LangChain
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_chunks = chunks[i : i + self.batch_size]
            batch_token_counts = token_counts[i : i + self.batch_size]
            
            # Generate embeddings using LangChain
            # This handles retries, rate limiting, etc. automatically
            embeddings = await self.embedder.aembed_documents(batch_texts)
            
            self.stats.api_calls += 1
            
            logger.debug(
                "batch_embedded",
                batch_size=len(batch_texts),
                embedding_dimensions=len(embeddings[0]) if embeddings else 0,
            )
            
            # Create results
            for chunk, embedding, tokens in zip(
                batch_chunks, embeddings, batch_token_counts
            ):
                results.append(
                    EmbeddingResult(
                        chunk_id=f"chunk_{chunk.chunk_index}",
                        embedding=embedding,
                        token_count=tokens,
                        model=self.stats.model,
                        provider=self.stats.provider,
                    )
                )
        
        elapsed = time.time() - start_time
        self.stats.processing_time_seconds += elapsed
        
        logger.info(
            "embedding_completed",
            chunk_count=len(chunks),
            elapsed_seconds=f"{elapsed:.2f}",
            total_cost=f"${self.stats.estimated_cost:.6f}",
            avg_ms_per_chunk=f"{(elapsed * 1000 / len(chunks)):.1f}",
        )
        
        return results
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text (e.g., search query).
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        
        Learning Notes:
        - Uses LangChain's aembed_query() method
        - Different from embed_documents() - optimized for queries
        """
        embedding = await self.embedder.aembed_query(text)
        
        logger.debug(
            "query_embedded",
            text_length=len(text),
            embedding_dimensions=len(embedding),
        )
        
        return embedding
    
    def get_stats(self) -> EmbeddingStats:
        """Get embedding statistics"""
        return self.stats
    
    def reset_stats(self):
        """Reset embedding statistics"""
        self.stats = EmbeddingStats(
            provider=settings.embedding.provider,
            model=self._get_model_name(),
        )
```

#### 1.3 Testing LangChain Embedding Service

```python
# tests/test_langchain_embeddings.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from semantic_search.embeddings import EmbeddingService, EmbeddingStats
from semantic_search.chunking.models import Chunk


@pytest.fixture
def mock_langchain_embedder():
    """Mock LangChain embeddings provider"""
    mock = AsyncMock()
    
    # Mock embed_documents (batch)
    mock.aembed_documents.return_value = [
        [0.1, 0.2, 0.3] * 512,  # 1536 dimensions
        [0.4, 0.5, 0.6] * 512,
    ]
    
    # Mock embed_query (single)
    mock.aembed_query.return_value = [0.7, 0.8, 0.9] * 512
    
    return mock


@pytest.mark.asyncio
async def test_embed_chunks_with_langchain(mock_langchain_embedder):
    """Test embedding generation using LangChain abstraction"""
    
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
    
    # Create service with mock embedder
    service = EmbeddingService(embedding_provider=mock_langchain_embedder)
    
    # Generate embeddings
    results = await service.embed_chunks(chunks)
    
    # Assertions
    assert len(results) == 2
    assert all(len(r.embedding) == 1536 for r in results)
    assert results[0].chunk_id == "chunk_0"
    assert results[1].chunk_id == "chunk_1"
    assert all(r.provider == "openai" for r in results)
    
    # Verify LangChain method was called
    mock_langchain_embedder.aembed_documents.assert_called_once()


@pytest.mark.asyncio
async def test_embed_query(mock_langchain_embedder):
    """Test single query embedding"""
    
    service = EmbeddingService(embedding_provider=mock_langchain_embedder)
    
    query = "kubernetes autoscaling"
    embedding = await service.embed_text(query)
    
    # Assertions
    assert len(embedding) == 1536
    
    # Verify LangChain query method was called
    mock_langchain_embedder.aembed_query.assert_called_once_with(query)


@pytest.mark.asyncio
async def test_provider_switching():
    """Test that providers can be swapped via configuration"""
    
    # This test demonstrates the power of LangChain abstraction
    # You can swap providers without changing application code
    
    with patch("semantic_search.embeddings.providers.settings") as mock_settings:
        mock_settings.embedding.provider = "openai"
        mock_settings.embedding.openai_api_key = "test-key"
        mock_settings.embedding.openai_model = "text-embedding-3-small"
        mock_settings.embedding.openai_dimensions = 1536
        mock_settings.embedding.max_retries = 3
        
        from semantic_search.embeddings.providers import get_embedding_provider
        
        provider = get_embedding_provider()
        
        # Should be OpenAI embeddings
        assert provider.__class__.__name__ == "OpenAIEmbeddings"


def test_cost_tracking():
    """Test cost tracking for different providers"""
    
    stats = EmbeddingStats(provider="openai", model="text-embedding-3-small")
    
    # text-embedding-3-small: $0.02 per 1M tokens
    stats.add_tokens(100_000)
    assert stats.estimated_cost == pytest.approx(0.002)
    
    # Test with Cohere model
    stats = EmbeddingStats(provider="cohere", model="embed-english-v3.0")
    stats.add_tokens(100_000)
    assert stats.estimated_cost == pytest.approx(0.01)
    
    # Test with Hugging Face (free)
    stats = EmbeddingStats(provider="huggingface", model="sentence-transformers")
    stats.add_tokens(100_000)
    assert stats.estimated_cost == 0.0


@pytest.mark.asyncio
async def test_two_tier_optimization(mock_langchain_embedder):
    """Test two-tier optimization with LangChain"""
    
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
    
    service = EmbeddingService(embedding_provider=mock_langchain_embedder)
    
    # Document is below threshold (600 tokens)
    results = await service.embed_chunks(
        chunks, 
        document_token_count=500
    )
    
    # Should still embed but log the optimization
    assert len(results) == 1
    assert service.stats.skipped_small_docs == 1
```

---

### Week 2: Vector Store Abstraction

*[Same as previous plan - this part doesn't change]*

The vector store abstraction remains identical to the previous plan. Key files:

- `src/semantic_search/storage/base.py` - IVectorStore interface
- `src/semantic_search/storage/cosmos_store.py` - Cosmos DB implementation
- `src/semantic_search/storage/factory.py` - Factory pattern

**No changes needed** - the storage layer is already provider-agnostic.

---

### Week 3: Complete Ingestion Pipeline with LangChain

#### 3.1 Pipeline Orchestrator

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
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"


class IngestionPipeline:
    """
    Complete ingestion pipeline with LangChain integration.
    
    Pipeline Flow:
    1. Load → Raw document from URL or file
    2. Process → HTML/Markdown to normalized format
    3. Chunk → Content-aware splitting
    4. Embed → LangChain embeddings (provider-agnostic)
    5. Store → Vector database with parent-child model
    
    Learning Notes:
    - Demonstrates LangChain embedding service integration
    - Shows provider-agnostic architecture
    - Prepares for Phase 2 LLM chains (summarization, tags)
    """
    
    def __init__(
        self,
        vector_store: Optional[IVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        enable_embedding: bool = True,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = (
            embedding_service or EmbeddingService() if enable_embedding else None
        )
        self.enable_embedding = enable_embedding
        
        # Processors
        self.web_processor = WebPageProcessor(include_enrichment=True)
        self.md_processor = MarkdownProcessor(include_enrichment=True)
        
        # Chunker
        self.chunker = MarkdownChunker(
            token_threshold=settings.embedding.small_doc_threshold,
        )
        
        logger.info(
            "pipeline_initialized",
            embedding_enabled=enable_embedding,
            embedding_provider=settings.embedding.provider if enable_embedding else None,
            storage_provider=settings.storage.provider,
        )
    
    async def initialize(self):
        """Initialize pipeline (create storage indexes, etc.)"""
        await self.vector_store.initialize()
        logger.info("pipeline_ready")
    
    def _generate_document_id(self, raw_doc: RawDocument) -> str:
        """Generate unique document ID from source"""
        if raw_doc.url:
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
        Execute complete ingestion pipeline with LangChain.
        
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
                embedding_provider=settings.embedding.provider,
                embedding_model=self.embedding_service.stats.model if self.embedding_service else "none",
            )
        
        # 4. Chunk document
        chunks = self.chunker.chunk_document(document.content)
        
        logger.info(
            "document_chunked",
            document_id=document_id,
            chunk_count=len(chunks),
        )
        
        # 5. Generate embeddings using LangChain (if enabled)
        chunks_with_embeddings = []
        estimated_cost = 0.0
        
        if self.enable_embedding and self.embedding_service:
            # Calculate total document token count
            doc_token_count = sum(chunk.token_count for chunk in chunks)
            
            # Embed chunks using LangChain
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
            
            logger.info(
                "embeddings_generated",
                provider=stats.provider,
                model=stats.model,
                total_cost=f"${estimated_cost:.6f}",
            )
        
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
            "embedding_provider": settings.embedding.provider if self.enable_embedding else None,
            "embedding_model": self.embedding_service.stats.model if self.embedding_service else None,
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
            embedding_provider=settings.embedding.provider if self.enable_embedding else "none",
            embedding_model=self.embedding_service.stats.model if self.embedding_service else "none",
        )
```

#### 3.2 Enhanced CLI with LangChain Support

```python
# src/semantic_search/ingestion_cli.py (enhanced for LangChain)

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .utils import fetch_url
from .models import RawDocument
from .pipeline import IngestionPipeline
from .storage import get_vector_store
from .config import settings

app = typer.Typer(
    help="Semantic Search Ingestion CLI with LangChain Integration"
)
console = Console()


@app.command()
def ingest(
    source: str = typer.Argument(..., help="URL or file path to ingest"),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for saving files (optional)",
    ),
    embed: bool = typer.Option(
        False,
        "--embed",
        help="Generate embeddings using LangChain",
    ),
    store: bool = typer.Option(
        False,
        "--store",
        help="Store in vector database",
    ),
    embedding_provider: Optional[str] = typer.Option(
        None,
        "--embedding-provider",
        help="Override embedding provider (openai|cohere|huggingface)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force re-indexing even if content unchanged",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output with detailed logging",
    ),
):
    """
    Ingest a document: Load → Process → Chunk → Embed (LangChain) → Store
    
    Examples:
    
        # Basic processing
        ingestion-cli https://example.com/article
        
        # With OpenAI embeddings (default)
        ingestion-cli https://example.com/article --embed
        
        # Complete pipeline with storage
        ingestion-cli https://example.com/article --embed --store
        
        # Use Cohere embeddings instead
        ingestion-cli https://example.com --embed --embedding-provider cohere
        
        # Process local markdown file
        ingestion-cli document.md --embed --store
    """
    
    # Override provider if specified
    if embedding_provider:
        import os
        os.environ["EMBEDDING_PROVIDER"] = embedding_provider
        console.print(
            f"[yellow]Using embedding provider: {embedding_provider}[/yellow]"
        )
    
    # Configure logging
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Run async ingestion
    asyncio.run(
        _ingest_async(
            source=source,
            output_dir=output_dir,
            embed=embed,
            store=store,
            force=force,
        )
    )


async def _ingest_async(
    source: str,
    output_dir: Optional[Path],
    embed: bool,
    store: bool,
    force: bool,
):
    """Async ingestion implementation with LangChain"""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Step 1: Load document
        task = progress.add_task("Loading document...", total=None)
        
        if source.startswith("http://") or source.startswith("https://"):
            raw_doc = await fetch_url(source)
        else:
            file_path = Path(source)
            if not file_path.exists():
                console.print(f"[red]Error: File not found: {source}[/red]")
                sys.exit(1)
            
            content = file_path.read_text(encoding="utf-8")
            
            if file_path.suffix.lower() in [".md", ".markdown"]:
                source_type = "markdown"
            elif file_path.suffix.lower() in [".html", ".htm"]:
                source_type = "web"
            else:
                source_type = "text"
            
            raw_doc = RawDocument(
                content=content,
                source_type=source_type,
                file_path=str(file_path),
            )
        
        progress.update(task, description="✓ Document loaded")
        
        # Step 2: Run pipeline with LangChain
        if embed or store:
            task = progress.add_task(
                f"Running pipeline (LangChain: {settings.embedding.provider})...",
                total=None
            )
            
            pipeline = IngestionPipeline(enable_embedding=embed)
            
            if store:
                await pipeline.initialize()
            
            result = await pipeline.ingest(raw_doc)
            
            progress.update(task, description="✓ Pipeline completed")
            
            # Display results
            console.print("\n[bold green]Ingestion Complete[/bold green]\n")
            
            table = Table(show_header=False)
            table.add_row("Document ID", result.document_id)
            table.add_row("Status", result.status)
            if result.reason:
                table.add_row("Reason", result.reason)
            table.add_row("Chunks", str(result.chunk_count))
            table.add_row("Tokens", f"{result.token_count:,}")
            if embed:
                table.add_row("Embedding Provider", result.embedding_provider)
                table.add_row("Embedding Model", result.embedding_model)
                table.add_row("Estimated Cost", f"${result.estimated_cost:.6f}")
            table.add_row(
                "Processing Time", 
                f"{result.processing_time_seconds:.2f}s"
            )
            
            console.print(table)
            
            if store and result.status in ["indexed", "updated"]:
                console.print(
                    f"\n[green]✓ Document stored in {settings.storage.provider}[/green]"
                )
        
        else:
            # Just process and save locally (no LangChain)
            from .processors import WebPageProcessor, MarkdownProcessor
            
            task = progress.add_task("Processing document...", total=None)
            
            if raw_doc.source_type == "web":
                processor = WebPageProcessor(include_enrichment=True)
            else:
                processor = MarkdownProcessor(include_enrichment=True)
            
            document = processor.process(raw_doc)
            
            progress.update(task, description="✓ Document processed")
            
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                
                md_file = output_dir / "document.md"
                md_file.write_text(document.content, encoding="utf-8")
                
                console.print(f"\n[green]✓ Saved to {md_file}[/green]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results"),
    source_type: Optional[str] = typer.Option(
        None,
        "--source",
        help="Filter by source type (web, markdown, etc.)",
    ),
):
    """
    Search indexed documents using LangChain embeddings.
    
    Example:
        ingestion-cli search "kubernetes autoscaling" --limit 5
    
    Note: Uses the same embedding provider as ingestion
    """
    asyncio.run(_search_async(query, limit, source_type))


async def _search_async(
    query: str,
    limit: int,
    source_type: Optional[str],
):
    """Async search implementation with LangChain"""
    
    from .embeddings import EmbeddingService
    
    console.print(
        f"\n[bold]Searching for:[/bold] {query}\n"
        f"[dim]Provider: {settings.embedding.provider}[/dim]\n"
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Generate query embedding using LangChain
        task = progress.add_task(
            f"Generating query embedding ({settings.embedding.provider})...",
            total=None
        )
        
        embedder = EmbeddingService()
        query_embedding = await embedder.embed_text(query)
        
        progress.update(task, description="✓ Query embedded")
        
        # Search vector store
        task = progress.add_task("Searching...", total=None)
        
        store = get_vector_store()
        await store.initialize()
        
        filters = {}
        if source_type:
            filters["source_types"] = [source_type]
        
        results = await store.vector_search(
            query_embedding=query_embedding,
            user_id=settings.storage.user_id,
            limit=limit,
            filters=filters if filters else None,
        )
        
        progress.update(task, description=f"✓ Found {len(results)} results")
    
    # Display results
    if not results:
        console.print("\n[yellow]No results found[/yellow]")
        return
    
    console.print(f"\n[bold green]Found {len(results)} results:[/bold green]\n")
    
    for i, result in enumerate(results, 1):
        console.print(f"[bold cyan]{i}. Score: {result.score:.3f}[/bold cyan]")
        console.print(f"   Document: {result.document_id}")
        console.print(f"   Section: {' > '.join(result.section_path)}")
        console.print(f"   Text: {result.text[:200]}...")
        console.print()


@app.command()
def info():
    """Display configuration information"""
    
    console.print("\n[bold]Current Configuration:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Embedding Provider", settings.embedding.provider)
    
    if settings.embedding.provider == "openai":
        table.add_row("Embedding Model", settings.embedding.openai_model)
        table.add_row("Dimensions", str(settings.embedding.openai_dimensions))
    elif settings.embedding.provider == "cohere":
        table.add_row("Embedding Model", settings.embedding.cohere_model)
    elif settings.embedding.provider == "huggingface":
        table.add_row("Embedding Model", settings.embedding.huggingface_model)
    
    table.add_row("Storage Provider", settings.storage.provider)
    table.add_row("User ID", settings.storage.user_id)
    table.add_row("Two-Tier Optimization", str(settings.embedding.enable_two_tier))
    table.add_row("Small Doc Threshold", f"{settings.embedding.small_doc_threshold} tokens")
    
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
```

---

### Week 4: Testing, Documentation & Phase 2 Preparation

#### 4.1 Integration Tests with LangChain

```python
# tests/test_langchain_integration.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from semantic_search.pipeline import IngestionPipeline
from semantic_search.models import RawDocument


@pytest.mark.asyncio
async def test_complete_pipeline_with_langchain():
    """Test complete pipeline with LangChain embeddings"""
    
    # Create mock vector store
    mock_store = AsyncMock()
    mock_store.get_document_hash.return_value = None
    mock_store.initialize.return_value = None
    mock_store.store_document.return_value = None
    
    # Create mock LangChain embedder
    mock_embedder = MagicMock()
    mock_embedder.aembed_documents = AsyncMock(
        return_value=[[0.1] * 1536]
    )
    
    # Create embedding service with mock
    from semantic_search.embeddings import EmbeddingService
    
    embedding_service = EmbeddingService(embedding_provider=mock_embedder)
    
    # Create pipeline
    pipeline = IngestionPipeline(
        vector_store=mock_store,
        embedding_service=embedding_service,
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
    assert result.embedding_provider == "openai"
    
    # Verify LangChain method was called
    mock_embedder.aembed_documents.assert_called()
    
    # Verify store was called
    mock_store.store_document.assert_called_once()


@pytest.mark.asyncio
async def test_provider_agnostic_pipeline():
    """Test that pipeline works with different embedding providers"""
    
    # This demonstrates the power of LangChain abstraction
    # Pipeline code doesn't change when swapping providers
    
    mock_store = AsyncMock()
    mock_store.get_document_hash.return_value = None
    mock_store.initialize.return_value = None
    mock_store.store_document.return_value = None
    
    # Mock any LangChain embedder
    mock_embedder = MagicMock()
    mock_embedder.aembed_documents = AsyncMock(
        return_value=[[0.1] * 768]  # Different dimensions (e.g., Cohere)
    )
    
    from semantic_search.embeddings import EmbeddingService
    
    embedding_service = EmbeddingService(embedding_provider=mock_embedder)
    
    pipeline = IngestionPipeline(
        vector_store=mock_store,
        embedding_service=embedding_service,
    )
    
    raw_doc = RawDocument(
        content="Test",
        source_type="markdown",
        file_path="/test.md",
    )
    
    result = await pipeline.ingest(raw_doc)
    
    # Pipeline works regardless of provider
    assert result.status in ["indexed", "updated", "skipped"]
```

#### 4.2 Documentation

Create comprehensive LangChain-focused documentation:

**1. `docs/langchain-integration.md`**

```markdown
# LangChain Integration Guide

## Overview

This project uses LangChain as the foundation for all AI operations, providing:

- **Provider-agnostic embeddings** - Easily swap between OpenAI, Cohere, Hugging Face
- **Unified interface** - Same code works with any provider
- **Built-in best practices** - Retry logic, rate limiting, error handling
- **Future-ready** - Prepared for Phase 2 LLM chains

## Embedding Providers

### OpenAI (Default)

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

**Pros:** High quality, 1536 dimensions, $0.02 per 1M tokens
**Cons:** Requires API key, external dependency

### Cohere

```bash
EMBEDDING_PROVIDER=cohere
COHERE_API_KEY=your-key
COHERE_EMBEDDING_MODEL=embed-english-v3.0
```

**Pros:** Multilingual support, good quality
**Cons:** $0.10 per 1M tokens (higher cost)

### Hugging Face (Local)

```bash
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Pros:** Free, runs locally, no API key needed
**Cons:** Lower quality, 384 dimensions, slower on CPU

## Swapping Providers

Simply change the environment variable:

```bash
# Switch to Cohere
export EMBEDDING_PROVIDER=cohere

# Run pipeline - no code changes needed!
ingestion-cli https://example.com --embed --store
```

## Phase 2 Preview: LLM Chains

In Phase 2, we'll add summarization and tag extraction using LangChain:

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Summarization chain (LCEL)
summary_prompt = ChatPromptTemplate.from_template("""
Summarize this in 2-3 sentences:

{content}
""")

llm = ChatAnthropic(model="claude-sonnet-4")

summary_chain = summary_prompt | llm | StrOutputParser()

# Use the chain
summary = await summary_chain.ainvoke({"content": document.content})
```

This is why we're using LangChain from the start!
```

**2. `docs/phase2-preview.md`**

```markdown
# Phase 2 Preview: Summarization & Tag Extraction

## What's Coming

Phase 2 will add AI-powered metadata extraction:

1. **Summarization** - 2-3 sentence summaries using Claude
2. **Tag Extraction** - Automatic tags from content
3. **Importance Scoring** - Relevance ranking (0-100)

## LangChain Foundation

Because we built Phase 1 with LangChain, adding these features is straightforward:

### Summarization Chain

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

summary_chain = (
    ChatPromptTemplate.from_template(
        "Summarize in 2-3 sentences:\n\n{content}"
    )
    | ChatAnthropic(model="claude-sonnet-4", temperature=0)
    | StrOutputParser()
)

summary = await summary_chain.ainvoke({"content": text})
```

### Tag Extraction with Structured Output

```python
from pydantic import BaseModel
from langchain_core.output_parsers import JsonOutputParser

class TagOutput(BaseModel):
    tags: list[str]

tag_chain = (
    ChatPromptTemplate.from_template(
        "Extract 3-5 technical tags:\n\n{content}\n\n{format_instructions}"
    )
    | ChatAnthropic(model="claude-sonnet-4")
    | JsonOutputParser(pydantic_object=TagOutput)
)

tags = await tag_chain.ainvoke({
    "content": text,
    "format_instructions": parser.get_format_instructions()
})
```

## Your Learning Path

By completing Phase 1 with LangChain, you've learned:

- ✅ Runnable interface
- ✅ Provider abstraction
- ✅ Async operations
- ✅ Error handling

Phase 2 will teach you:

- 🔄 LCEL chaining with `|`
- 🔄 Prompt templates
- 🔄 Output parsers
- 🔄 Structured outputs
- 🔄 RAG patterns
```

---

## 🎓 Learning Resources

### LangChain Concepts to Master

1. **Runnables** - Base abstraction for all components
   - Read: https://python.langchain.com/docs/expression_language/interface

2. **Embeddings** - Text-to-vector transformation
   - Read: https://python.langchain.com/docs/modules/data_connection/text_embedding/

3. **LCEL** - LangChain Expression Language
   - Read: https://python.langchain.com/docs/expression_language/

4. **Chains** - Combining components
   - Read: https://python.langchain.com/docs/modules/chains/

### Recommended Learning Path

**Week 1:** 
- Implement OpenAI embeddings with LangChain
- Understand Runnable interface
- Test provider swapping

**Week 2:**
- Integrate with vector store
- Learn error handling patterns
- Understand async operations

**Week 3:**
- Build complete pipeline
- Test with multiple providers
- Optimize performance

**Week 4:**
- Read LCEL documentation
- Build simple summarization chain (practice)
- Prepare for Phase 2

---

## 📊 Success Metrics

Track these metrics to validate your LangChain integration:

### Functional Metrics

- [ ] Can swap embedding providers via config (OpenAI ↔ Cohere ↔ Hugging Face)
- [ ] LangChain retries work on rate limits
- [ ] Embeddings generated with correct dimensions
- [ ] Vector search returns relevant results
- [ ] Pipeline works with all three providers

### Learning Metrics

- [ ] Understand Runnable interface
- [ ] Can explain provider abstraction benefits
- [ ] Know how to use LCEL `|` operator
- [ ] Ready to build summarization chains (Phase 2)

### Performance Metrics

- [ ] LangChain overhead: <50ms per batch
- [ ] Provider switching: Zero code changes
- [ ] Error handling: Graceful retries on failures

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Activate environment
.venv\Scripts\activate

# Install with LangChain
pip install -e .[dev]

# Optional: Install alternative providers
pip install -e .[cohere]       # For Cohere
pip install -e .[huggingface]  # For local embeddings
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env and add your keys
# Minimum required:
OPENAI_API_KEY=sk-...
COSMOS_ENDPOINT=https://...
COSMOS_KEY=...
```

### 3. Test LangChain Integration

```python
# test_langchain.py
import asyncio
from semantic_search.embeddings import EmbeddingService

async def test():
    service = EmbeddingService()
    
    # Embed a test query
    embedding = await service.embed_text("kubernetes autoscaling")
    
    print(f"✓ Generated {len(embedding)}-dimensional embedding")
    print(f"✓ Provider: {service.stats.provider}")
    print(f"✓ Model: {service.stats.model}")

asyncio.run(test())
```

### 4. Run Complete Pipeline

```bash
# Basic: Process and chunk
ingestion-cli https://example.com/article

# With OpenAI embeddings
ingestion-cli https://example.com/article --embed

# With Cohere embeddings
ingestion-cli https://example.com/article --embed --embedding-provider cohere

# Complete pipeline: embed and store
ingestion-cli https://example.com/article --embed --store

# Search
ingestion-cli search "kubernetes autoscaling"
```

---

## 🎯 Summary

This LangChain-integrated plan provides:

✅ **Provider-agnostic architecture** - Swap embeddings without code changes  
✅ **Learning foundation** - Hands-on with LangChain core concepts  
✅ **Future-ready** - Prepared for Phase 2 LLM chains  
✅ **Production-quality** - Error handling, retries, monitoring  
✅ **Cost-optimized** - Two-tier chunking saves 70-80%

**Your learning journey:**

1. **Week 1-2:** Master LangChain embeddings and provider abstraction
2. **Week 3-4:** Build complete pipeline and understand LCEL basics
3. **Phase 2:** Apply knowledge to build summarization and tag extraction chains

**Estimated completion:** 4-6 weeks of focused development

Good luck with your LangChain learning journey! 🚀
