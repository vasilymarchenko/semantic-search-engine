---
name: semantic-search-python
description: >
  Python coding standards for the semantic-search-engine project. Use this skill
  whenever writing or reviewing ANY Python code in this project — connectors,
  processors, embedding pipeline, models, config, tests. Covers modern Python 3.11+
  patterns that LLMs frequently regress on: Pydantic v2 syntax, async structured
  concurrency, type unions, Protocol-based plugin architecture, and project conventions.
  Always consult before generating Pydantic models, async pipeline code, or connector
  implementations.
---

# Python Standards — Semantic Search Engine

**Python version: 3.11+**  
**Key libs: Pydantic v2, pydantic-settings, LangChain (LCEL), azure-cosmos, asyncio**

Before generating Pydantic models → read `references/pydantic-v2.md`  
Before generating async pipeline code → read `references/async-patterns.md`

---

## 1. Type Syntax — Always Use 3.10+ Forms

```python
# ❌ Never — pre-3.10 style (LLM default regression)
from typing import Optional, List, Union, Dict, Tuple
def process(items: List[str]) -> Optional[Document]: ...

# ✅ Always — 3.10+ built-in generics and union syntax
def process(items: list[str]) -> Document | None: ...
def merge(a: dict[str, int], b: dict[str, int]) -> dict[str, int]: ...
def coords() -> tuple[float, float]: ...

# Type aliases — use `type` keyword (3.12) or TypeAlias (3.10/3.11)
from typing import TypeAlias
ChunkId: TypeAlias = str
EmbeddingVector: TypeAlias = list[float]
```

No imports from `typing` except: `Protocol`, `TypeAlias`, `TypeVar`, `Generic`,
`overload`, `TYPE_CHECKING`, `runtime_checkable`, `Any`, `ClassVar`, `Literal`.

---

## 2. Protocol for Plugin Interfaces (not ABC)

The project has a plugin architecture: multiple connectors, multiple chunkers.
Use `Protocol` — structural typing means connectors don't inherit anything.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SourceConnector(Protocol):
    """Structural interface — implementors need not inherit this."""
    async def fetch(self, source_id: str) -> list[RawDocument]: ...
    async def authenticate(self) -> bool: ...

@runtime_checkable  
class ChunkingStrategy(Protocol):
    def chunk(self, document: Document) -> list[Chunk]: ...
    @property
    def strategy_name(self) -> str: ...
```

Use `isinstance(obj, SourceConnector)` checks only need `@runtime_checkable`.

---

## 3. Self-Registering Plugin Registry

For connector/chunker discovery without manual registration:

```python
class ConnectorRegistry:
    _registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, *, source_type: str, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        ConnectorRegistry._registry[source_type] = cls

    @classmethod
    def get(cls, source_type: str) -> type:
        if source_type not in cls._registry:
            raise KeyError(f"Unknown connector: {source_type!r}")
        return cls._registry[source_type]


class TelegramConnector(ConnectorRegistry, source_type="telegram"):
    async def fetch(self, source_id: str) -> list[RawDocument]: ...

class ObsidianConnector(ConnectorRegistry, source_type="obsidian"):
    async def fetch(self, source_id: str) -> list[RawDocument]: ...

# Usage
connector_cls = ConnectorRegistry.get("telegram")
connector = connector_cls(settings)
```

---

## 4. Configuration — pydantic-settings

Never use `os.getenv()` directly. All config through a `Settings` class:

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Azure
    cosmos_endpoint: str
    cosmos_key: SecretStr
    cosmos_database: str = "semantic-search"

    # OpenAI
    openai_api_key: SecretStr
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100

    # Connectors
    telegram_api_id: int | None = None
    telegram_api_hash: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",   # for Azure Key Vault mount
        case_sensitive=False,
    )

# Singleton — instantiate once at module level
settings = Settings()

# Access secrets safely
api_key = settings.openai_api_key.get_secret_value()
```

---

## 5. Pathlib — Always, Never os.path

```python
from pathlib import Path

# ❌ Never
import os
path = os.path.join(base_dir, "data", "docs")
files = [f for f in os.listdir(path) if f.endswith(".md")]

# ✅ Always
base_dir = Path(__file__).parent
data_dir = base_dir / "data" / "docs"
files = list(data_dir.glob("**/*.md"))

# Common patterns
content = path.read_text(encoding="utf-8")
path.write_text(content, encoding="utf-8")
path.mkdir(parents=True, exist_ok=True)
relative = path.relative_to(base_dir)
stem = path.stem          # filename without extension
suffix = path.suffix      # ".md"
```

---

## 6. Error Handling

```python
import contextlib

# Suppress specific exceptions cleanly
with contextlib.suppress(FileNotFoundError):
    cache_path.unlink()

# Re-raise with context
try:
    result = await connector.fetch(source_id)
except httpx.TimeoutException as e:
    raise IngestionError(f"Connector timed out: {source_id}") from e

# Custom exception hierarchy — project convention
class SemanticSearchError(Exception):
    """Base for all project errors."""

class IngestionError(SemanticSearchError):
    """Raised when document ingestion fails."""

class EmbeddingError(SemanticSearchError):
    """Raised when embedding generation fails."""

class ConnectorAuthError(SemanticSearchError):
    """Raised when connector authentication fails."""
```

ExceptionGroup + `except*` — see `references/async-patterns.md` (TaskGroup errors).

---

## 7. Logging

Use structured logging. Never bare `print()` in pipeline code.

```python
import logging

logger = logging.getLogger(__name__)  # module-level, never pass around

# ✅ Use lazy % formatting, not f-strings in log calls
logger.info("Indexed %d chunks from document %s", chunk_count, doc_id)
logger.debug("Embedding batch size: %d", len(batch))
logger.exception("Failed to process document %s", doc_id)  # includes traceback

# ✅ Structured extra fields
logger.info(
    "Chunk indexed",
    extra={"doc_id": doc_id, "chunk_index": i, "token_count": tokens},
)
```

---

## 8. General Conventions

**Immutable value objects** — use `frozen=True` for domain models that shouldn't change after creation (see Pydantic reference).

**`__slots__`** — on hot-path dataclasses (e.g., `Chunk`) to reduce memory for thousands of instances.

**Dict merge** (3.9+):
```python
merged = base_metadata | source_metadata  # new dict
base_metadata |= overrides                 # in-place
```

**Walrus operator** for assignment in conditions:
```python
if chunk := chunker.next():
    await pipeline.process(chunk)
```

**`match`/`case`** for source type dispatch (3.10+):
```python
match document.source_type:
    case "telegram":
        return TelegramChunker().chunk(document)
    case "obsidian" | "pdf":
        return MarkdownChunker().chunk(document)
    case _:
        raise ValueError(f"Unknown source type: {document.source_type!r}")
```
