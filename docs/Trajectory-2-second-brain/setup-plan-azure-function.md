# Setup Plan — Azure Function Initial Implementation

**Branch:** `claude/trajectory-2-setup-plan-yHnRs`  
**Scope:** Sprint 1 — end-to-end skeleton for `POST /api/inbox/external`  
**Goal:** Save a URL → get title + summary back → find it via vector search  
**Design authority:** ADR-005, ADR-006, ADR-007, ADR-008 (see `ADR-second-brain-trajectory.md`)

---

## 1. Repository Layout

New directories alongside existing `src/` and `tests/`:

```
semantic-search-engine/
├── src/semantic_search/          # existing Phase 1 library
│   ├── models.py                 # ✅ keep — Chunk/ContentBlock (notes pipeline)
│   ├── models_v2.py              # 🆕 ExternalItem + supporting types
│   ├── processors/               # ✅ keep — WebPageProcessor reused as-is
│   ├── chunking/                 # ✅ keep — notes pipeline only
│   ├── sources/                  # 🆕 source detection + content acquisition
│   │   ├── __init__.py
│   │   ├── detector.py           # URL → SourceType (deterministic, no LLM)
│   │   └── extractors.py        # ContentExtractor Protocol + impls
│   ├── processing/               # 🆕 LLM interpretation layer
│   │   ├── __init__.py
│   │   ├── external_processor.py # Sonnet summarisation + key_concepts
│   │   └── skills_loader.py     # local file / Azure Blob backend
│   ├── pipeline/
│   │   ├── ingestion.py          # ✅ keep for notes pipeline
│   │   └── embedder.py          # 🆕 ExternalEmbedder + dedup
│   └── config.py                # 🆕 pydantic-settings Settings class
│
├── functions/                    # 🆕 Azure Functions app root
│   ├── host.json
│   ├── requirements.txt
│   ├── local.settings.json.template
│   └── inbox_external/
│       ├── function.json
│       └── __init__.py          # HTTP trigger — orchestrates pipeline
│
├── skills/                       # 🆕 LLM skill files (blob-synced in prod)
│   └── sources/
│       ├── article.md
│       └── youtube.md
│
└── tests/
    ├── test_detector.py          # 🆕 unit tests — URL pattern matching
    ├── test_extractors.py        # 🆕 integration tests — real URLs
    └── ... (existing)
```

---

## 2. Azure Function Scaffold

### 2.1 `functions/host.json`

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": { "isEnabled": true }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

### 2.2 `functions/requirements.txt`

```
azure-functions==1.21.*
# Phase 1 library (editable install in dev, wheel in prod)
semantic-search @ file://../
# LLM / embedding
langchain>=0.2.0
langchain-anthropic>=0.1.0
langchain-openai>=0.1.0
# Source-specific acquisition
youtube-transcript-api>=0.6.0
pypdf>=4.0.0
aiohttp>=3.9.0          # already in Phase 1
# Storage
azure-cosmos>=4.7.0
azure-storage-blob>=12.19.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

### 2.3 `functions/local.settings.json.template`

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "COSMOS_ENDPOINT": "https://<account>.documents.azure.com:443/",
    "COSMOS_KEY": "<key>",
    "COSMOS_DATABASE": "semantic-search",
    "COSMOS_CONTAINER": "items",

    "OPENAI_API_KEY": "<key>",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",

    "ANTHROPIC_API_KEY": "<key>",
    "ROUTER_MODEL": "claude-haiku-4-5-20251001",
    "PROCESSOR_MODEL": "claude-sonnet-4-6",

    "SKILLS_BACKEND": "local",
    "SKILLS_LOCAL_PATH": "../../skills",
    "SKILLS_BLOB_CONNECTION": "",
    "SKILLS_BLOB_CONTAINER": "skills"
  }
}
```

### 2.4 `functions/inbox_external/function.json`

```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "route": "inbox/external",
      "methods": ["POST"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

---

## 3. Configuration (`src/semantic_search/config.py`)

Single `Settings` class — the only place `os.getenv` is allowed.

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Cosmos DB
    cosmos_endpoint: str
    cosmos_key: SecretStr
    cosmos_database: str = "semantic-search"
    cosmos_container: str = "items"

    # OpenAI embeddings
    openai_api_key: SecretStr
    openai_embedding_model: str = "text-embedding-3-small"

    # Anthropic / Claude
    anthropic_api_key: SecretStr
    router_model: str = "claude-haiku-4-5-20251001"
    processor_model: str = "claude-sonnet-4-6"

    # Skills
    skills_backend: str = "local"           # "local" | "blob"
    skills_local_path: str = "skills"
    skills_blob_connection: str = ""
    skills_blob_container: str = "skills"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
```

LangChain model instances wired from settings — never hardcoded in pipeline:

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings

PROCESSOR_LLM = ChatAnthropic(
    model=settings.processor_model,
    api_key=settings.anthropic_api_key.get_secret_value(),
)
EMBEDDINGS = OpenAIEmbeddings(
    model=settings.openai_embedding_model,
    api_key=settings.openai_api_key.get_secret_value(),
)
```

---

## 4. Data Model (`src/semantic_search/models_v2.py`)

Extends Phase 1 without touching existing `models.py`.

```python
from __future__ import annotations

import hashlib
from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ExternalItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str                          # sha256(url)[:16]
    type: Literal["external"] = "external"
    user_id: str

    title: str
    summary: str                     # 2-3 sentences, Claude-generated
    key_concepts: list[str]          # ["kubernetes", "autoscaling"]
    source_url: str
    source_type: str                 # article | video | tweet | pdf
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    my_note: str | None = None

    embedding: list[float]
    content_hash: str                # sha256(url) — dedup key

    @classmethod
    def url_hash(cls, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]


class RawContent(BaseModel):
    """Output of a ContentExtractor — raw text before LLM processing."""
    model_config = ConfigDict(frozen=True)

    text: str
    title: str | None = None
    metadata: dict = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Structured output from LLM interpretation of raw content."""
    model_config = ConfigDict(frozen=True)

    title: str
    summary: str
    key_concepts: list[str]
    error: str | None = None         # "insufficient_content" | None
```

---

## 5. Source Detection (`src/semantic_search/sources/detector.py`)

Deterministic URL-pattern dispatch — zero tokens, zero latency.

```python
from __future__ import annotations

import re
from enum import StrEnum


class SourceType(StrEnum):
    ARTICLE  = "article"
    VIDEO    = "video"
    TWEET    = "tweet"
    TELEGRAM = "telegram_post"
    PDF      = "pdf"


# Ordered: first match wins. Catch-all ARTICLE is the implicit default.
_PATTERNS: list[tuple[SourceType, list[str]]] = [
    (SourceType.VIDEO,    [r"youtube\.com/watch", r"youtu\.be/"]),
    (SourceType.TWEET,    [r"twitter\.com/\w+/status", r"x\.com/\w+/status"]),
    (SourceType.TELEGRAM, [r"t\.me/"]),
    (SourceType.PDF,      [r"\.pdf(?:$|\?)", r"/pdf/"]),
]


def detect_source_type(url: str) -> SourceType:
    """
    Map URL to acquisition strategy via regex patterns.
    Falls back to ARTICLE (HTTP + HTML parser) for all unmatched URLs.
    """
    for source_type, patterns in _PATTERNS:
        if any(re.search(p, url, re.IGNORECASE) for p in patterns):
            return source_type
    return SourceType.ARTICLE
```

**Edge cases to cover in tests:**
- `youtu.be/dQw4w9WgXcQ` → `VIDEO`
- `youtube.com/shorts/abc123` → `ARTICLE` (shorts not supported in MVP — falls through)
- `t.me/channelname/123` → `TELEGRAM`
- `example.com/report.pdf?v=2` → `PDF`
- `example.com/some-pdf-guide` → `ARTICLE` (path contains "pdf" but no `.pdf` extension)
- `twitter.com/user` (profile, not tweet) → `ARTICLE`
- `x.com/user/status/123456` → `TWEET`

---

## 6. Content Acquisition (`src/semantic_search/sources/extractors.py`)

Protocol-based — no ABC inheritance required by implementors (per project standards).

```python
from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from semantic_search.models_v2 import RawContent
from semantic_search.sources.detector import SourceType

logger = logging.getLogger(__name__)


@runtime_checkable
class ContentExtractor(Protocol):
    async def extract(self, url: str) -> RawContent: ...


# --- Sprint 1: ArticleExtractor (reuses Phase 1 code) ---

class ArticleExtractor:
    """
    HTTP fetch → readability → markdown.
    Reuses existing fetch_url + WebPageProcessor — effectively zero new code.
    Covers articles, blogs, docs, Substack, newsletters, GitHub READMEs.
    """

    async def extract(self, url: str) -> RawContent:
        from semantic_search.utils.fetcher import fetch_url
        from semantic_search.processors.web import WebPageProcessor

        raw_doc = await fetch_url(url)
        processor = WebPageProcessor(include_enrichment=False)
        doc = processor.process(raw_doc)

        return RawContent(
            text=doc.content,
            title=doc.title,
            metadata=doc.metadata,
        )


# --- Sprint 2: YouTubeExtractor ---

class YouTubeExtractor:
    """
    youtube-transcript-api → concatenated transcript text.
    Falls back to ArticleExtractor if transcript unavailable.
    """

    async def extract(self, url: str) -> RawContent:
        from youtube_transcript_api import YouTubeTranscriptApi
        import asyncio

        video_id = self._parse_video_id(url)
        transcript_list = await asyncio.to_thread(
            YouTubeTranscriptApi.get_transcript, video_id
        )
        text = " ".join(segment["text"] for segment in transcript_list)
        return RawContent(text=text, metadata={"video_id": video_id})

    @staticmethod
    def _parse_video_id(url: str) -> str:
        import re
        patterns = [r"youtu\.be/([^?&]+)", r"v=([^?&]+)"]
        for pattern in patterns:
            if m := re.search(pattern, url):
                return m.group(1)
        raise ValueError(f"Cannot parse video ID from: {url}")


# --- Sprint 2: PDFExtractor ---

class PDFExtractor:
    """pypdf text extraction from downloaded PDF."""

    async def extract(self, url: str) -> RawContent:
        import io
        import asyncio
        import aiohttp
        import pypdf

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()

        def _read_pdf(data: bytes) -> str:
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )

        text = await asyncio.to_thread(_read_pdf, data)
        return RawContent(text=text)


# --- Extractor registry: SourceType → extractor instance ---

EXTRACTOR_REGISTRY: dict[SourceType, ContentExtractor] = {
    SourceType.ARTICLE:  ArticleExtractor(),
    SourceType.VIDEO:    YouTubeExtractor(),
    SourceType.PDF:      PDFExtractor(),
    # TWEET, TELEGRAM: added in Sprint 3
}

_article_fallback = ArticleExtractor()


def get_extractor(source_type: SourceType) -> ContentExtractor:
    return EXTRACTOR_REGISTRY.get(source_type, _article_fallback)
```

**Reading strategy by source type:**

| Source type | Acquisition method | Key consideration |
|---|---|---|
| `article` | HTTP GET → readability → markdown | Reuses Phase 1 `WebPageProcessor` |
| `video` | `youtube-transcript-api` (sync → `asyncio.to_thread`) | Falls back to article if no transcript |
| `pdf` | `aiohttp` download → `pypdf` text extraction | Binary download, sync PDF parsing off-thread |
| `tweet` | Twitter/X oEmbed API (no auth for public) | Sprint 3 |
| `telegram_post` | Preview page scrape (public channels only) | Sprint 3 |

---

## 7. Content Interpretation (`src/semantic_search/processing/`)

### 7.1 Skills Loader

```python
# src/semantic_search/processing/skills_loader.py

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillsLoader:
    """
    Loads skill prompt files from local filesystem (dev) or Azure Blob (prod).
    Controlled by SKILLS_BACKEND env var: 'local' | 'blob'.
    Cache loaded files in-process to avoid repeated I/O.
    """

    def __init__(self, backend: str, local_path: str, blob_connection: str, blob_container: str):
        self._backend = backend
        self._local_root = Path(local_path)
        self._blob_connection = blob_connection
        self._blob_container = blob_container
        self._cache: dict[str, str] = {}

    async def load(self, path: str, fallback: str | None = None) -> str:
        if path in self._cache:
            return self._cache[path]
        try:
            content = await self._read(path)
            self._cache[path] = content
            return content
        except FileNotFoundError:
            if fallback:
                logger.warning("Skill %s not found, using fallback %s", path, fallback)
                return await self.load(fallback)
            raise

    async def _read(self, path: str) -> str:
        if self._backend == "local":
            full = self._local_root / path
            if not full.exists():
                raise FileNotFoundError(path)
            return full.read_text(encoding="utf-8")
        else:
            return await self._read_blob(path)

    async def _read_blob(self, path: str) -> str:
        import asyncio
        from azure.storage.blob import BlobServiceClient

        def _sync() -> str:
            client = BlobServiceClient.from_connection_string(self._blob_connection)
            blob = client.get_container_client(self._blob_container).get_blob_client(path)
            return blob.download_blob().readall().decode("utf-8")

        return await asyncio.to_thread(_sync)
```

### 7.2 External Processor

```python
# src/semantic_search/processing/external_processor.py

from __future__ import annotations

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from semantic_search.models_v2 import ProcessedContent, RawContent
from semantic_search.processing.skills_loader import SkillsLoader
from semantic_search.sources.detector import SourceType

logger = logging.getLogger(__name__)

_MAX_CONTENT_TOKENS = 4000
_CHARS_PER_TOKEN = 4  # conservative approximation


class ExternalProcessor:
    def __init__(self, llm: BaseChatModel, skills_loader: SkillsLoader):
        self._llm = llm
        self._skills = skills_loader

    async def process(self, raw: RawContent, source_type: SourceType) -> ProcessedContent:
        skill = await self._skills.load(
            f"sources/{source_type}.md",
            fallback="sources/article.md",
        )

        text = self._truncate(raw.text)
        if raw.title:
            text = f"Title: {raw.title}\n\n{text}"

        response = await self._llm.ainvoke([
            SystemMessage(content=skill),
            HumanMessage(content=text),
        ])

        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("LLM returned non-JSON: %s", response.content[:200])
            return ProcessedContent(
                title=raw.title or "Unknown",
                summary="",
                key_concepts=[],
                error="invalid_llm_response",
            )

        return ProcessedContent(**data)

    @staticmethod
    def _truncate(text: str) -> str:
        max_chars = _MAX_CONTENT_TOKENS * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[content truncated]"
```

### 7.3 Skill Files

**`skills/sources/article.md`**
```
You are processing a saved web article for a personal knowledge base.

Extract:
- title: the article title (infer if not explicit)
- summary: 2-3 sentences capturing the core idea. Be specific enough to
  remind the user why they saved this.
- key_concepts: 3-8 lowercase keywords including both explicit terms AND
  semantically related concepts useful for future search.

If content is low-quality, paywalled, or empty, return:
{ "error": "insufficient_content" }

Respond ONLY with valid JSON. No markdown fences, no explanation.
```

**`skills/sources/youtube.md`**
```
You are processing a YouTube video transcript for a personal knowledge base.

The input is raw auto-generated transcript — expect informal language,
no punctuation, and possible transcription errors. Infer meaning from context.

Extract:
- title: infer from content if not provided
- summary: 2-3 sentences on the video's main argument or teaching
- key_concepts: 3-8 keywords; prefer the speaker's own terminology

If transcript is too short or uninformative, return:
{ "error": "insufficient_content" }

Respond ONLY with valid JSON. No markdown fences, no explanation.
```

---

## 8. Embedding + Dedup (`src/semantic_search/pipeline/embedder.py`)

```python
from __future__ import annotations

import hashlib

from langchain_core.embeddings import Embeddings

from semantic_search.models_v2 import ExternalItem, ProcessedContent


class ExternalEmbedder:
    def __init__(self, embeddings: Embeddings):
        self._embeddings = embeddings

    async def embed(self, processed: ProcessedContent, my_note: str | None) -> list[float]:
        text = self._embed_text(processed, my_note)
        return await self._embeddings.aembed_query(text)

    @staticmethod
    def _embed_text(processed: ProcessedContent, my_note: str | None) -> str:
        parts = [processed.summary]
        if processed.key_concepts:
            parts.append(" ".join(processed.key_concepts))
        if my_note:
            parts.append(f"Note: {my_note}")
        return " ".join(parts)

    @staticmethod
    def url_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]
```

---

## 9. Azure Function Endpoint (`functions/inbox_external/__init__.py`)

The HTTP trigger orchestrates all pipeline steps in order.

```python
from __future__ import annotations

import json
import logging

import azure.functions as func

from semantic_search.config import settings, PROCESSOR_LLM, EMBEDDINGS
from semantic_search.models_v2 import ExternalItem
from semantic_search.pipeline.embedder import ExternalEmbedder
from semantic_search.processing.external_processor import ExternalProcessor
from semantic_search.processing.skills_loader import SkillsLoader
from semantic_search.sources.detector import detect_source_type
from semantic_search.sources.extractors import get_extractor

logger = logging.getLogger(__name__)

# Module-level singletons (constructed once per cold start)
_skills_loader = SkillsLoader(
    backend=settings.skills_backend,
    local_path=settings.skills_local_path,
    blob_connection=settings.skills_blob_connection,
    blob_container=settings.skills_blob_container,
)
_processor = ExternalProcessor(llm=PROCESSOR_LLM, skills_loader=_skills_loader)
_embedder = ExternalEmbedder(embeddings=EMBEDDINGS)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    # --- Input validation ---
    try:
        body = req.get_json()
        url: str = body["url"]
    except (ValueError, KeyError):
        return _bad_request("Request body must be JSON with a 'url' field.")

    if not url.startswith(("http://", "https://")):
        return _bad_request("'url' must be an absolute HTTP/HTTPS URL.")

    my_note: str | None = body.get("my_note")

    # --- Dedup ---
    url_hash = ExternalEmbedder.url_hash(url)
    # TODO: check Cosmos DB for existing item with id == url_hash
    # if existing: return _ok({"status": "duplicate", "id": url_hash})

    # --- Source detection ---
    source_type = detect_source_type(url)
    logger.info("Detected source type %s for %s", source_type, url)

    # --- Content acquisition ---
    extractor = get_extractor(source_type)
    try:
        raw = await extractor.extract(url)
    except Exception as exc:
        logger.exception("Extraction failed for %s", url)
        return _error({"status": "extraction_failed", "reason": str(exc)})

    if not raw.text.strip():
        return _error({"status": "extraction_failed", "reason": "empty_content"})

    # --- LLM interpretation ---
    processed = await _processor.process(raw, source_type)
    if processed.error:
        return _error({"status": "processing_failed", "reason": processed.error})

    # --- Embedding ---
    embedding = await _embedder.embed(processed, my_note)

    # --- Store ---
    item = ExternalItem(
        id=url_hash,
        user_id="default",           # single-user MVP; extend later
        title=processed.title,
        summary=processed.summary,
        key_concepts=processed.key_concepts,
        source_url=url,
        source_type=source_type,
        my_note=my_note,
        embedding=embedding,
        content_hash=url_hash,
    )
    # TODO: await cosmos_client.upsert_item(item.model_dump())

    logger.info("Indexed %s as %s", url, item.id)
    return _ok({"status": "indexed", "id": item.id, "title": item.title, "summary": item.summary})


def _ok(data: dict) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(data), mimetype="application/json", status_code=200)

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"error": msg}), mimetype="application/json", status_code=400)

def _error(data: dict) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(data), mimetype="application/json", status_code=422)
```

---

## 10. Implementation Order (Sprint 1 checklist)

### Day 1 — Data model + config
- [ ] `src/semantic_search/models_v2.py` — `ExternalItem`, `RawContent`, `ProcessedContent`
- [ ] `src/semantic_search/config.py` — `Settings` with pydantic-settings
- [ ] `tests/test_models_v2.py` — validate field defaults, `url_hash` determinism, frozen model

### Day 2 — Source detection + article extractor
- [ ] `src/semantic_search/sources/__init__.py`
- [ ] `src/semantic_search/sources/detector.py` — `SourceType` + `detect_source_type`
- [ ] `tests/test_detector.py` — URL pattern edge cases (see §5 above)
- [ ] `src/semantic_search/sources/extractors.py` — `ContentExtractor` Protocol + `ArticleExtractor`
- [ ] Verify `ArticleExtractor` round-trips through `fetch_url` + `WebPageProcessor`

### Day 3 — LLM interpretation layer
- [ ] `src/semantic_search/processing/skills_loader.py` — local backend first
- [ ] `skills/sources/article.md` — skill prompt
- [ ] `src/semantic_search/processing/external_processor.py`
- [ ] `tests/test_external_processor.py` — mock LLM, test JSON parse + truncation
- [ ] Manual smoke test: feed a real article URL, inspect summary quality

### Day 4 — Embedding + Function scaffold
- [ ] `src/semantic_search/pipeline/embedder.py` — `ExternalEmbedder`
- [ ] `functions/host.json`, `functions/requirements.txt`, `functions/local.settings.json.template`
- [ ] `functions/inbox_external/function.json` + `__init__.py` (Cosmos stubs as TODO)
- [ ] Update `pyproject.toml` — add new optional deps group `[trajectory-2]`

### Day 5 — Integration + local run
- [ ] `func start` in `functions/` — verify endpoint responds
- [ ] End-to-end test: `curl -X POST .../api/inbox/external -d '{"url":"..."}'`
- [ ] Verify dedup path (same URL twice → second call skips extraction)
- [ ] Add `YouTubeExtractor` + `skills/sources/youtube.md`

---

## 11. Open Questions Resolved for Sprint 1

| Question | Decision |
|---|---|
| Cosmos DB for Sprint 1? | Use stub (`# TODO`) on Day 4; wire real Cosmos on Day 5 |
| Auth on the endpoint? | `authLevel: function` (key-based) — sufficient for personal use |
| Token truncation | First 4000 tokens (16 000 chars) — covers most articles; revisit for YouTube |
| Extraction failure handling | Return 422 with `status: extraction_failed` — do not store partial items |
| YouTube Shorts? | Out of scope for Sprint 1 — falls through to `ArticleExtractor` |
| LinkedIn / Facebook? | Excluded from MVP — require auth |

---

## 12. Key Design Constraints (from ADRs)

- **ADR-005:** One embedding per external item, no chunking, no full-text storage.
- **ADR-006:** Layer 1 (acquisition) is code; Layer 2 (interpretation) is skill files. Adding a new web source type = new `.md` file only.
- **ADR-007:** `POST /api/inbox/external` is the single entry point for all URL types; routing is internal.
- **ADR-008:** All LLM/embedding calls go through LangChain interfaces. Models configured via environment variables, never hardcoded.
- **Project standard:** Protocol over ABC, pydantic-settings over `os.getenv`, Python 3.11+ type syntax throughout.
