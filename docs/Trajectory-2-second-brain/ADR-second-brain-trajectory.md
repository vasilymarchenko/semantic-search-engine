# Architecture Decision Records — Second Brain Trajectory

**Project:** semantic-search-engine  
**Date:** May 2026  
**Status:** Accepted

---

## ADR-005: Memory Model over RAG for External Content

### Context

The original architecture treated all content sources uniformly: fetch → chunk → embed chunks → store. This was designed for a RAG use case where the goal is to retrieve relevant *passages* from a knowledge base in response to detailed queries.

During design review, the primary use case was re-examined:

> *"I saved this article/video/post. Later I want to find it again — where did I see something about X?"*

This is a **memory retrieval** problem, not a passage retrieval problem. The user wants to find the *source*, not a paragraph within it. The original source is still available at the URL.

### Decision

Apply two distinct storage and indexing strategies based on content origin:

| Content Type | Strategy | Embedding Target | Full Text Stored? |
|---|---|---|---|
| External (articles, videos, posts) | Summary-based | `summary + my_note` | ❌ URL is the reference |
| Personal notes (Obsidian) | Chunk-based | Per chunk | ✅ No URL to go back to |

**External items** are indexed with a single embedding per document, generated from a Claude-produced summary (2–3 sentences) plus an optional user annotation. The original content lives at the source URL.

**Personal notes** retain the original chunking strategy from Phase 1 — full text stored, multiple chunk embeddings, offset-based references. The user's own writing has no canonical external source.

### Consequences

- ✅ Dramatically simpler ingestion for external content (no chunking step)
- ✅ Lower embedding cost — one vector per external item vs. 5–15
- ✅ Lower storage cost — no full-text duplication for external content
- ✅ Search results are actionable: "you saved this → [link]"
- ✅ Existing chunking library remains valid for Obsidian notes
- ⚠️ Cannot answer "what exactly did that article say about X" — by design, go read the source
- ⚠️ Summary quality determines search quality — model choice matters

---

## ADR-006: Two-Layer Source Handling — Code for Acquisition, Skills for Interpretation

### Context

A question arose: should the skills selector determine how to handle new source types, or should source handling be code-based? The original draft of this ADR proposed pure code-based extraction, but this was challenged on agility grounds.

The core tension:
- **Code-only approach:** new source type = new Python class = redeployment. Fast and deterministic, but loses extensibility.
- **Skills-only approach:** new source type = new text file = no redeployment. Agile, but a text file cannot make an HTTP request or call the YouTube API.

### Decision

**Source handling is split into two distinct layers with different extensibility models.**

**Layer 1 — Content Acquisition (code)**

*How to get the raw bytes.* Deterministic URL pattern matching selects an acquisition strategy:

```
youtube.com, youtu.be  →  YouTube Transcript API
t.me/*                 →  Telegram preview scrape
twitter.com, x.com     →  Twitter/X API
*.pdf                  →  PDF text extraction
*  (default)           →  HTTP fetch + HTML parser  ← covers ~90% of web
```

This layer is **small and stable** — there are at most 5–7 meaningful acquisition patterns. New ones are rare and genuinely require code. Each extractor is written once.

Critically, the default HTTP extractor already covers the vast majority of web content (articles, blog posts, documentation, newsletters, Substack, etc.) without any new code.

**Layer 2 — Content Interpretation (skills)**

*How to understand what was fetched.* A skill file loaded from Azure Blob Storage instructs the LLM on how to process this content type:

```
skills/sources/article.md          ← general web article
skills/sources/youtube.md          ← video transcript, focus on spoken content
skills/sources/academic_paper.md   ← extract abstract, methodology, conclusions
skills/sources/newsletter.md       ← digest format, key links, main topics
skills/sources/tweet_thread.md     ← capture argument arc across thread
skills/sources/docs_page.md        ← technical reference, APIs, examples
```

**Adding a new source type:**

| New source | Acquisition | Interpretation | Code change? |
|---|---|---|---|
| Substack post | HTTP (default) ✅ | New `substack.md` skill | ❌ None |
| Podcast transcript | HTTP (default) ✅ | New `podcast.md` skill | ❌ None |
| GitHub README | HTTP (default) ✅ | New `github_readme.md` skill | ❌ None |
| YouTube video | YouTube API ⚠️ | New `youtube.md` skill | ✅ Once |
| Twitter/X thread | Twitter API ⚠️ | New `tweet_thread.md` skill | ✅ Once |

The pipeline flow:

```
URL
 ↓
[Code]   detect acquisition strategy  (URL pattern match)
 ↓
[Code]   acquire raw content          (HTTP / YouTube API / etc.)
 ↓
[Code]   load skills/sources/{source_type}.md from Blob Storage
 ↓
[Sonnet] process with skill  →  { title, summary, key_concepts }
 ↓
[Code]   embed + store
```

### Consequences

- ✅ Extensibility lives in text files — the common case (new web source) requires no code
- ✅ Acquisition layer is fast, deterministic, zero token cost
- ✅ Interpretation layer is fully swappable — improve a skill without touching code
- ✅ Clear boundary: code answers "how do I get the bytes", skills answer "how do I understand them"
- ✅ ~90% of web sources covered by default HTTP extractor from day one
- ⚠️ Special acquisition sources (YouTube, Twitter) still require code — but only once per source
- ⚠️ Some sources (LinkedIn, Facebook) require auth — excluded from MVP scope
- ⚠️ Skill file must exist for the detected source type; fallback to `article.md` if not found

---

## ADR-007: Single Ingestion Endpoint with Internal Source Routing

### Context

Should external content (URLs) and internal notes (Obsidian) be separate Azure Function endpoints?

### Decision

**Yes — separate HTTP endpoints, shared storage layer.**

```
POST /api/inbox/external   ←  URLs from any interface
POST /api/inbox/notes      ←  Obsidian sync (future, timer-triggered)
```

Rationale:
- Different triggers: external is event-driven (user saves something), notes sync is timer-driven
- Different pipelines: external has no chunking, notes do
- Different auth/input shapes: URL vs. file path
- Shared: Cosmos DB container, embedding service, LangChain config

Within `/api/inbox/external`, source-type routing is internal to the function — a URL pattern matcher dispatches to the appropriate extractor. No separate endpoint per source type.

### Consequences

- ✅ Clean interface — one endpoint for "I found something on the web"
- ✅ Each pipeline evolves independently
- ✅ Notes sync can be added later without touching external pipeline
- ⚠️ Function app grows — needs clean internal module structure from the start

---

## ADR-008: LangChain as Orchestration Layer with Configurable Models

### Context

The project uses Claude (Anthropic) and OpenAI. Vendor lock-in is a concern. Different tasks have different cost/quality requirements.

### Decision

All LLM and embedding calls go through **LangChain interfaces**. Models are configured externally, never hardcoded in business logic.

```python
# config.py — swap models without changing pipeline code
ROUTER_LLM    = ChatAnthropic(model=env("ROUTER_MODEL"))      # Haiku
PROCESSOR_LLM = ChatAnthropic(model=env("PROCESSOR_MODEL"))   # Sonnet
EMBEDDINGS    = OpenAIEmbeddings(model=env("EMBEDDING_MODEL")) # text-embedding-3-small
```

**Model tier assignments:**

| Task | Tier | Rationale |
|---|---|---|
| Source classification / routing | Haiku | Simple decision, ~200 tokens |
| Summary + key concept extraction | Sonnet | Quality drives search quality |
| Obsidian note summarization | Haiku | Short docs, low complexity |
| Query / Q&A over results | Sonnet | Reasoning required |

### Consequences

- ✅ Provider swap is a config change
- ✅ Cost optimization built into architecture
- ✅ Consistent pattern across all pipeline stages
- ⚠️ LangChain abstraction adds a dependency — acceptable given learning goal

---

## What Carries Forward from Phase 1

| Component | Disposition |
|---|---|
| `processors/web.py` — HTML fetcher & parser | ✅ Kept — feeds raw content into new pipeline |
| `chunking/` — content-aware chunker | ✅ Kept — used for Obsidian notes only |
| Pydantic models (`ContentBlock`, `Chunk`) | ✅ Kept for notes pipeline |
| Cosmos DB `document` + `chunk` schema | ⚠️ Extended — new `external` type added |
| Phase 1 embedding pipeline | ✅ Kept for notes; skipped for external |
| Feed aggregator connector designs | ⚠️ Revisited — Telegram/email become source types in inbox pipeline |
