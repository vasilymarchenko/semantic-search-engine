# Pydantic v2 Reference

**This project uses Pydantic v2. LLMs frequently generate v1 syntax — catch it.**

---

## Renamed Methods (v1 → v2)

| v1 (❌ Never use) | v2 (✅ Always use) |
|---|---|
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj(data)` | `Model.model_validate(data)` |
| `.parse_raw(json_str)` | `Model.model_validate_json(json_str)` |
| `.copy(update={...})` | `.model_copy(update={...})` |
| `.schema()` | `Model.model_json_schema()` |
| `__fields__` | `model_fields` |

---

## Config: `ConfigDict` Replaces Inner `class Config`

```python
from pydantic import BaseModel, ConfigDict

# ❌ v1 — never write this
class Document(BaseModel):
    class Config:
        frozen = True
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# ✅ v2
class Document(BaseModel):
    model_config = ConfigDict(
        frozen=True,           # immutable after creation
        populate_by_name=True, # accept both alias and field name
        str_strip_whitespace=True,
        validate_assignment=True,  # re-validate on attribute set (if not frozen)
    )
```

---

## Domain Models for This Project

```python
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# --- Value objects: frozen, no embeddings ---

class RawDocument(BaseModel):
    """Output of a SourceConnector — unprocessed."""
    model_config = ConfigDict(frozen=True)

    source_type: Literal["telegram", "obsidian", "email", "github", "pdf"]
    source_id: str
    content: str                        # raw text / HTML / markdown
    content_type: Literal["html", "markdown", "text", "code"]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Processed, normalized document stored in Cosmos DB (no embedding)."""
    model_config = ConfigDict(frozen=True)

    id: str                             # Cosmos DB document id
    source_type: str
    source_id: str
    text: str                           # full normalized text — stored ONCE here
    language: str | None = None
    created_at: datetime
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field                     # v2: replaces @property for serialization
    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()

    @computed_field
    @property
    def char_count(self) -> int:
        return len(self.text)


class Chunk(BaseModel):
    """Chunk item — stores offsets + embedding, NOT the text."""
    model_config = ConfigDict(frozen=True)

    id: str
    document_id: str                    # FK to parent Document
    chunk_index: int
    char_start: int
    char_end: int
    token_count: int
    preview: str                        # ~200 chars for display without DB roundtrip
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

## Validators — v2 Syntax

```python
from pydantic import field_validator, model_validator

class Document(BaseModel):
    id: str
    text: str
    source_type: str

    # ✅ v2 field validator — must be @classmethod
    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"telegram", "obsidian", "email", "github", "pdf"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}, got {v!r}")
        return v

    # ✅ v2 field validator — mode='before' runs before type coercion
    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    # ✅ v2 model validator — runs after all field validation
    @model_validator(mode="after")
    def validate_id_matches_source(self) -> Document:
        if not self.id.startswith(self.source_type):
            raise ValueError(f"id {self.id!r} should start with source_type {self.source_type!r}")
        return self
```

---

## Field Aliases and Serialization

```python
from pydantic import Field, AliasChoices

class CosmosDocument(BaseModel):
    """Maps between Python naming and Cosmos DB's '_id' field."""
    model_config = ConfigDict(populate_by_name=True)

    # Accept 'id' or '_id' when reading from Cosmos
    id: str = Field(validation_alias=AliasChoices("id", "_id"))

    # Serialize as '_rid' when writing to Cosmos
    resource_id: str | None = Field(None, serialization_alias="_rid")

# Serialization options
doc.model_dump()                                # Python field names
doc.model_dump(by_alias=True)                   # serialization aliases
doc.model_dump(exclude_none=True)               # omit None fields
doc.model_dump(include={"id", "text"})          # only specific fields
doc.model_dump(exclude={"embedding"})           # exclude heavy fields
doc.model_dump_json(exclude_none=True)          # JSON string directly
```

---

## SecretStr for Sensitive Values

```python
from pydantic import SecretStr

class ConnectorCredentials(BaseModel):
    api_key: SecretStr
    api_hash: SecretStr | None = None

creds = ConnectorCredentials(api_key="secret123")
print(creds.api_key)                    # SecretStr('**********')
print(creds.api_key.get_secret_value()) # "secret123"
creds.model_dump()                      # {"api_key": "**********"}
creds.model_dump(mode="json")           # {"api_key": "**********"}
```

---

## Custom Types

```python
from pydantic import field_validator
from typing import Annotated
from pydantic.functional_validators import AfterValidator

def _non_empty(v: str) -> str:
    if not v.strip():
        raise ValueError("must not be empty")
    return v

NonEmptyStr = Annotated[str, AfterValidator(_non_empty)]

class Chunk(BaseModel):
    preview: NonEmptyStr       # validated automatically
```
