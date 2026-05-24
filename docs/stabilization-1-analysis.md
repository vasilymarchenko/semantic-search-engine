# Stabilization-1 Analysis: PR #1 vs Trajectory-2 Plans

**Date:** 2026-05-24  
**PR:** [#1 — Azure Function initial setup](https://github.com/vasilymarchenko/semantic-search-engine/pull/1)  
**Branch merged:** `claude/trajectory-2-setup-plan-yHnRs` → `master`  
**Plans reviewed:** `docs/Trajectory-2-second-brain/setup-plan-azure-function.md` and `docs/Trajectory-2-second-brain/implementation-plan-inbox-external.md`

---

## 1. What Was Planned

The trajectory-2 plans covered a 5-day Sprint 1 to build a working end-to-end skeleton for `POST /api/inbox/external` — the URL ingestion pipeline for external content (articles, videos, PDFs). The pipeline steps were:

| Step | Component | Goal |
|---|---|---|
| 0 | `models_v2.py` | Data model: `ExternalItem`, `RawContent`, `ProcessedContent` |
| 1 | `sources/detector.py` | Deterministic URL → SourceType regex dispatch |
| 2 | `sources/extractors.py` | `ContentExtractor` Protocol + `ArticleExtractor` (Sprint 1), YouTube + PDF stubs |
| 3 | `processing/` | `SkillsLoader` + `ExternalProcessor` (Sonnet-based summarisation) |
| 4 | `pipeline/embedder.py` | `ExternalEmbedder` + URL-hash dedup |
| 5 | `functions/` | Azure Function HTTP trigger orchestrating steps 0–4 |

The setup plan also called for the Azure Function to use a **v1-style layout** (`functions/inbox_external/__init__.py` + `function.json`), and for LLM/embedding singletons to be module-level constants (`PROCESSOR_LLM`, `EMBEDDINGS`) imported directly from `config.py`.

---

## 2. What Was Done (PR #1 — 26 files, +2516 / -19)

### 2.1 New files created

| File | Purpose |
|---|---|
| `src/semantic_search/config.py` | `Settings` via pydantic-settings; all env vars in one place |
| `src/semantic_search/models_v2.py` | `ExternalItem`, `RawContent`, `ProcessedContent`; `url_hash()` helper |
| `src/semantic_search/sources/__init__.py` | Package marker |
| `src/semantic_search/sources/detector.py` | `SourceType` (StrEnum) + `detect_source_type()` |
| `src/semantic_search/sources/extractors.py` | `ContentExtractor` Protocol + `ArticleExtractor`, `YouTubeExtractor`, `PDFExtractor` |
| `src/semantic_search/processing/__init__.py` | Package marker |
| `src/semantic_search/processing/skills_loader.py` | `SkillsLoader` with local + Azure Blob backends, in-process cache |
| `src/semantic_search/processing/external_processor.py` | `ExternalProcessor` — skill loading + Sonnet invocation + JSON parse |
| `src/semantic_search/pipeline/embedder.py` | `ExternalEmbedder` — embedding text assembly + OpenAI embedding call |
| `functions/function_app.py` | Azure Functions v2 app — `POST /api/inbox/external` HTTP trigger |
| `functions/host.json` | Runtime config (extension bundle 4.x) |
| `functions/requirements.txt` | Function-level dependency list |
| `functions/local.settings.json.template` | Local dev environment variable template |
| `skills/sources/article.md` | System prompt for article summarisation |
| `skills/sources/youtube.md` | System prompt for YouTube transcript summarisation |
| `tests/test_detector.py` | Parametrised URL pattern tests (edge cases including Shorts, profile pages) |
| `tests/test_models_v2.py` | Tests for `url_hash`, `ExternalItem.build()`, frozen model constraints |
| `tests/test_external_processor.py` | Mock-LLM tests for JSON parse, truncation, error handling |
| `tests/test_embedder.py` | Tests for embedding text assembly (`summary + key_concepts + my_note`) |
| `pyproject.toml` | Added `[trajectory-2]` optional dependency group |

### 2.2 Notable implementation differences from the plan

| Area | Plan | Actual implementation |
|---|---|---|
| Azure Function layout | v1 style: `functions/inbox_external/__init__.py` + `function.json` | **v2 style**: single `functions/function_app.py` with `@app.route()` decorator |
| LLM/embeddings construction | Module-level constants `PROCESSOR_LLM`, `EMBEDDINGS` in `config.py` | Lazy singletons via `_build_processor()` / `_build_embedder()` + `_get_*()` accessors — avoids import-time credential errors |
| `ContentExtractor` | Planned as ABC (`class ContentExtractor(ABC)`) | Implemented as `Protocol` with `@runtime_checkable` — matches project standards (Protocol over ABC) |
| `ExternalItem` constructor | Direct `__init__` | Added `ExternalItem.build()` classmethod — cleaner call site |
| `url_hash` | Method on `ExternalItem` (`cls.url_hash`) | Extracted to module-level `url_hash()` function in `models_v2.py`; `ExternalEmbedder.item_id()` delegates to it |
| `ExternalEmbedder._embed_text` | Includes only `summary + my_note` | Also includes `key_concepts` — richer embedding signal |
| `detect_source_type` video pattern | `r"youtube\.com"` (any youtube URL) | Tightened to `r"youtube\.com/watch"` — YouTube Shorts/channel pages fall through to ARTICLE |
| `detect_source_type` PDF pattern | `r"\.pdf($|\?)"` | Also adds `r"/download/.*\.pdf"` for download-style URLs |
| `SkillsLoader._read` | `if/else` on backend string | `match/case` statement |
| `PDFExtractor` | No timeout | `asyncio.timeout(60.0)` wrapping HTTP download |
| `YouTubeExtractor` fallback | Not in plan | Gracefully falls back to `ArticleExtractor` on `TranscriptsDisabled`/`NoTranscriptFound` |

---

## 3. What Is NOT Done (gaps against the plan)

### 3.1 Cosmos DB integration — not wired

The two most critical `TODO` stubs in `function_app.py` are:

```python
# --- Dedup check ---
item_id = ExternalEmbedder.item_id(url)
# TODO: check Cosmos DB — if item with id == item_id exists, return duplicate
# existing = await _cosmos_container().read_item(item_id, partition_key="default")
# if existing: return _ok({"status": "duplicate", "id": item_id})

# --- Store ---
# TODO: await _cosmos_container().upsert_item(item.model_dump(exclude={"embedding"}))
# TODO: store embedding in vector index
```

The plan explicitly deferred Cosmos wiring to Day 5 and called it out as a stub, but the plan also stated Day 5 was to verify the dedup path (same URL twice → second call skips extraction). This is currently dead code — neither the read nor the write path is wired.

### 3.2 Vector index / embedding storage — not wired

Cosmos DB currently has no vector index configured for `external` type items. The embedding is generated but discarded — never persisted. Vector search over external items is therefore not functional.

### 3.3 Dedup check — non-functional

Because Cosmos is not wired, duplicate URL submissions are not detected. Each call to `POST /api/inbox/external` with the same URL re-fetches, re-processes, and re-embeds, then discards the result.

### 3.4 `inbox_external/function.json` — not created

The setup plan specified a separate `functions/inbox_external/` subdirectory with `function.json` + `__init__.py`. The actual implementation uses the Azure Functions v2 programming model (`function_app.py` with decorators) which does not need `function.json`. This is a valid and better approach — it is not a deficiency, but a deliberate divergence.

### 3.5 `tests/test_extractors.py` — not created

The plan listed integration tests for real URL extraction. These were not added in PR #1. The extractors are covered only via type-checking — no live fetch tests exist.

### 3.6 `func start` smoke test — not documented

The Day 5 checklist item ("verify endpoint responds", "end-to-end curl test") is not documented as completed. Given that Cosmos is unconnected, a full end-to-end success path cannot be verified.

### 3.7 Sprint 2 extractors — stubs present, not tested

`YouTubeExtractor` and `PDFExtractor` are fully implemented (not stubs), but:
- No dedicated tests exist for them.
- They are wired into `_REGISTRY` and will be called in production for VIDEO and PDF source types.

### 3.8 Tweet and Telegram extractors — absent

`TweetExtractor` and `TelegramExtractor` are noted as "Sprint 3" in code comments. The registry falls back to `ArticleExtractor` for these types — which will typically return empty or low-quality content for those URLs.

---

## 4. Current Endpoint Behaviour — What Happens When Called

### Request

```
POST /api/inbox/external
Content-Type: application/json

{ "url": "https://example.com/some-article", "my_note": "optional" }
```

### Step-by-step execution

**1. Input validation**

The function parses JSON, checks that `url` is present, starts with `http://` or `https://`, and is ≤ 2048 characters. Failures return `400`.

**2. Dedup check (skipped)**

`ExternalEmbedder.item_id(url)` computes `sha256(url)[:16]`. The Cosmos DB read is commented out — no dedup occurs. Every call proceeds regardless of whether the URL was seen before.

**3. Source type detection**

`detect_source_type(url)` runs regex patterns in order:
- `youtube.com/watch` or `youtu.be/<id>` → `VIDEO`
- `twitter.com/.../status/` or `x.com/.../status/` → `TWEET`
- `t.me/` → `TELEGRAM`
- `.pdf` (extension) or `/download/...pdf` → `PDF`
- Everything else → `ARTICLE`

**4. Content acquisition**

The appropriate extractor is called:

- **ARTICLE** (`ArticleExtractor`): Calls `fetch_url(url)` (aiohttp), passes HTML to `WebPageProcessor` which runs readability + markdownify, returns `RawContent(text, title, metadata)`.
- **VIDEO** (`YouTubeExtractor`): Extracts the video ID from the URL, calls `YouTubeTranscriptApi.get_transcript()` in a thread pool. On `TranscriptsDisabled`/`NoTranscriptFound`, falls back to `ArticleExtractor`.
- **PDF** (`PDFExtractor`): Downloads the PDF with a 60s timeout, runs `pypdf.PdfReader` in a thread pool, returns concatenated page text.
- **TWEET** / **TELEGRAM**: No registered extractor — falls back to `ArticleExtractor`. For most tweet/Telegram URLs this will return poor content.

On any exception during extraction → `422 { "status": "extraction_failed", "reason": "fetch_error" }`.  
If extracted text is blank → `422 { "status": "extraction_failed", "reason": "empty_content" }`.

**5. LLM interpretation**

`ExternalProcessor.process()` is called:

1. Loads `skills/sources/<source_type>.md` from local filesystem (or Azure Blob in production). Falls back to `skills/sources/article.md` if the file does not exist.
2. Truncates content to 16 000 characters (~4 000 tokens).
3. Prepends `"Title: <title>\n\n"` if a title was extracted.
4. Calls `ChatAnthropic` (claude-sonnet-4-6) with system = skill prompt, human = truncated content.
5. Parses the response as JSON. On parse failure → `ProcessedContent(error="invalid_llm_response")`.
6. If JSON contains `"error"` key → `ProcessedContent(error=<value>)`.

On error → `422 { "status": "processing_failed", "reason": "<error>" }`.

**6. Embedding**

`ExternalEmbedder.embed()` concatenates `summary + key_concepts (space-joined) + "Note: <my_note>"` and calls `OpenAIEmbeddings.aembed_query()` (text-embedding-3-small). Returns a `list[float]`.

**7. Item construction**

`ExternalItem.build()` creates a frozen Pydantic model with:
- `id` = `sha256(url)[:16]`
- `type` = `"external"`
- `user_id` = `"default"` (hardcoded — single-user MVP)
- `title`, `summary`, `key_concepts` from `ProcessedContent`
- `source_url`, `source_type`, `saved_at`, `my_note`
- `embedding` = the embedding vector
- `content_hash` = same as `id`

**8. Storage (skipped)**

Both Cosmos DB upsert calls are commented out. The item is constructed in memory and logged, then discarded. Nothing is persisted.

**9. Response**

Returns `200`:
```json
{
  "status": "indexed",
  "id": "<sha256(url)[:16]>",
  "title": "<LLM-extracted title>",
  "summary": "<LLM-generated summary>"
}
```

### Effective result

The endpoint is **functional but stateless**. It correctly fetches, processes, and embeds content — but does not persist anything. Each call is idempotent by accident (no side effects). The pipeline can be validated end-to-end for correctness of the extraction + LLM + embedding steps, but search over external items is impossible since no data reaches Cosmos DB.

---

## 5. Summary Table

| Area | Status | Notes |
|---|---|---|
| Azure Function scaffold (v2) | ✅ Done | v2 decorator model instead of v1 folders |
| `Settings` config class | ✅ Done | Defaults guard against missing env vars at import time |
| `ExternalItem` / `RawContent` / `ProcessedContent` | ✅ Done | `ExternalItem.build()` classmethod added |
| `SourceType` + `detect_source_type` | ✅ Done | Tighter patterns than plan (no false-positive YouTube URLs) |
| `ArticleExtractor` | ✅ Done | Reuses Phase 1 `WebPageProcessor` as planned |
| `YouTubeExtractor` | ✅ Done | Fully implemented with fallback; not in Sprint 1 plan scope |
| `PDFExtractor` | ✅ Done | With 60s timeout; not in Sprint 1 plan scope |
| `TweetExtractor` | ❌ Not done | Sprint 3 — falls back to `ArticleExtractor` |
| `TelegramExtractor` | ❌ Not done | Sprint 3 — falls back to `ArticleExtractor` |
| `SkillsLoader` (local + blob) | ✅ Done | In-process cache included |
| `ExternalProcessor` | ✅ Done | JSON error handling, title prepend, truncation |
| `skills/sources/article.md` | ✅ Done | More detailed than plan version |
| `skills/sources/youtube.md` | ✅ Done | |
| `ExternalEmbedder` | ✅ Done | Embeds `summary + key_concepts + my_note` |
| Cosmos DB — dedup read | ❌ Not done | TODO stub |
| Cosmos DB — item write | ❌ Not done | TODO stub |
| Vector index — embedding write | ❌ Not done | TODO stub |
| Unit tests — detector | ✅ Done | Edge cases covered |
| Unit tests — models_v2 | ✅ Done | |
| Unit tests — external_processor | ✅ Done | Mock LLM |
| Unit tests — embedder | ✅ Done | |
| Integration tests — extractors | ❌ Not done | `test_extractors.py` not created |
| `func start` / curl smoke test | ❌ Not verified | Cosmos stubs prevent full end-to-end |
