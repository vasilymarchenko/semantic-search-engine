# Second Brain — Personal Knowledge Engine

A personal AI-powered memory system that captures everything you read, watch, and save — and makes it instantly findable.

---

## The Problem

You save dozens of links a week. Articles, YouTube videos, Twitter threads, PDFs, documentation pages. A month later you remember *something* about Kubernetes autoscaling, or a paper on RAG architectures, or that blog post about team communication — but not where you saw it. Bookmarks don't help. They only know titles, and you have thousands of them.

The deeper problem isn't storage. It's retrieval. You need a system that understands what you saved, not just where.

---

## What We're Building

A personal knowledge engine with two core capabilities:

**1. Omni-source inbox**
Send any URL — article, YouTube video, PDF, tweet, documentation page — and the system captures it. It reads the content, generates a meaningful summary, extracts key concepts, and indexes it semantically. No manual tagging. No friction.

**2. Natural language search**
Ask "where did I see something about distributed tracing?" and get back: *"You saved this article in March → [link]"* or *"You wrote about this in your Obsidian note → [passage]"*. The answer points you back to the source, not a chunk of text extracted from it.

The system also indexes your **Obsidian vault** — your own writing — with deeper search that surfaces specific passages, not just note titles.

---

## Key Ideas

### Memory retrieval, not RAG

Most search systems built on vector embeddings are optimised for RAG — retrieving passages to feed into an LLM answer. That's the wrong model for a personal knowledge base.

When you ask "where did I read about X?", you want the *source back*, not a synthesised answer. The original article, video, or note is still there. The job is to find it.

This distinction drives the entire architecture:
- External content (articles, videos, posts) → indexed by summary, one embedding per item
- Personal notes (Obsidian) → indexed by content, chunk-level embeddings for deep search

### Two-layer source extensibility

Adding support for a new content source is split into two concerns:

**Content acquisition** (code) — how to get the raw text. HTTP fetch, YouTube Transcript API, PDF extraction. A small, stable set of patterns. The HTTP fetcher alone covers the vast majority of web content with no new code.

**Content interpretation** (skill files) — how to understand what was fetched. Each source type has a text-file skill that instructs the AI on what to extract and how to summarise. Adding a new source type means creating a new `.md` skill file — no redeployment.

```
skills/sources/
├── article.md          ← general web article (default fallback)
├── youtube.md          ← video transcripts
├── academic_paper.md   ← abstract, methodology, conclusions
├── newsletter.md       ← digest format, key links
└── tweet_thread.md     ← argument arc
```

### Skills as configuration

All AI behaviour is defined in plain text skill files stored in Azure Blob Storage and loaded at runtime. Changing how the system processes content means editing a text file, not rewriting code.

### LangChain for provider agnosticism

All LLM and embedding calls go through LangChain interfaces. Models are configuration, not code. Swapping Claude for GPT-4o, or OpenAI embeddings for a local model, is a one-line config change.

Different tasks use different model tiers deliberately:

| Task | Model tier | Why |
|---|---|---|
| Source type classification | Haiku | Simple decision, ~200 tokens |
| Summary + concept extraction | Sonnet | Quality drives search quality |
| Obsidian note summarisation | Haiku | Short docs, low complexity |
| Query / Q&A over results | Sonnet | Reasoning required |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              INTERFACES                     │
│   Telegram  │  Chrome Extension  │  API     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         POST /api/inbox/external            │
│                                             │
│  [Code]   Detect acquisition strategy       │
│  [Code]   Acquire raw content               │
│  [Code]   Load skills/sources/{type}.md     │
│  [Sonnet] Summarise + extract concepts      │
│  [Code]   Embed (summary + my_note)         │
│  [Code]   Dedup check (SHA-256 on URL)      │
│  [Code]   Store in Cosmos DB                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           COSMOS DB                         │
│  external items  │  obsidian notes          │
│  (1 embedding)   │  (chunk embeddings)      │
└─────────────────────────────────────────────┘
```

---

## Storage Model

Two document types in the same Cosmos DB container:

**External** — saved content from the web
```json
{
  "type": "external",
  "title": "...",
  "summary": "2-3 sentences, Claude-generated",
  "key_concepts": ["kubernetes", "autoscaling"],
  "source_url": "https://...",
  "source_type": "article | video | tweet | post | pdf",
  "saved_at": "...",
  "my_note": "optional annotation",
  "embedding": [...]
}
```

**Note** — your Obsidian vault
```json
{
  "type": "note",
  "title": "...",
  "summary": "...",
  "full_text": "...",
  "source_path": "Notes/DevOps/keda.md",
  "hash": "sha256:...",
  "chunks": [
    { "index": 0, "start": 0, "end": 500, "embedding": [...] }
  ]
}
```

---

## What's Built

The project evolved from an initial RAG/semantic search engine. The document processing foundation from that phase carries forward:

| Component | Status |
|---|---|
| HTML → Markdown processor | ✅ Complete |
| Content-aware chunker (600-token threshold) | ✅ Complete |
| Pydantic models, type safety | ✅ Complete |
| CLI for local ingestion testing | ✅ Complete |
| External inbox pipeline | 🔄 In progress |
| Skills infrastructure (Blob loader) | 🔄 In progress |
| Cosmos DB vector store | 🔄 In progress |
| Query / search API | 📋 Planned |
| Telegram bot interface | 📋 Planned |
| Chrome extension | 📋 Planned |
| Obsidian vault sync | 📋 Planned |

---

## Tech Stack

- **Python 3.11+** — ingestion pipeline, AI processing
- **Azure Functions** — serverless compute, HTTP triggers, timer triggers
- **Azure Cosmos DB** — document store with native vector search
- **Azure Blob Storage** — skill files, configuration
- **LangChain** — LLM and embedding abstraction layer
- **OpenAI** — `text-embedding-3-small` for vectors
- **Anthropic Claude** — summarisation, concept extraction, Q&A

---

## Documentation

- [Architecture Decision Records](docs/Trajectory-2-second-brain/ADR-second-brain-trajectory.md) — key design decisions and the reasoning behind the shift from RAG to memory model
- [Original Project Plan](docs/Trajectory-1-RAG-system/semantic-search-engine-plan.md) — full original architecture and Phase 1 implementation details
- [Chunking Strategy Guide](docs/Trajectory-1-RAG-system/chunking-guide.md) — content-aware chunking for Obsidian notes

---

## Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux

# Install with dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=semantic_search --cov-report=html

# Lint and format
ruff check src/ tests/ --fix
black src/ tests/
```

## Run The Azure Function Locally (Step By Step)

This section is for the `POST /api/inbox/external` endpoint implemented in `functions/function_app.py`.

### 1. Prerequisites

- Python 3.11+
- Docker Desktop (for the Azurite storage emulator)
- Azure Functions Core Tools v4 (`func` command)
- Access to:
  - Anthropic API key
  - OpenAI API key
- Optional for current local MVP:
  - Cosmos DB credentials (code paths are scaffolded, persistence is still TODO)

Check tools:

```bash
python --version
func --version
```

### 2. Create And Activate Virtual Environment

From repository root:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies For Function + Trajectory 2

From repository root:

```bash
python -m pip install -e .[dev]
python -m pip install -r functions/requirements.txt
```

PowerShell note: if you install extras directly, quote them to avoid wildcard parsing:

```powershell
python -m pip install -e '.[trajectory-2]'
```

### 4. Create Local Function Settings File

Copy the template:

Windows PowerShell:

```powershell
Copy-Item functions\local.settings.json.template functions\local.settings.json
```

macOS/Linux:

```bash
cp functions/local.settings.json.template functions/local.settings.json
```

Then edit `functions/local.settings.json` and set at least:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `PROCESSOR_MODEL` (default in template is fine)
- `OPENAI_EMBEDDING_MODEL` (default in template is fine)
- `SKILLS_BACKEND` = `local`
- `SKILLS_LOCAL_PATH` = `../skills`

Note: this function app currently reads from `skills/sources/*.md`, so `SKILLS_LOCAL_PATH` must resolve to the repo `skills` folder when running from `functions/`.

### 5. Start The Storage Emulator

The Functions runtime requires Azure Storage access for internal coordination. Locally this is served by Azurite, which runs via Docker Compose. The `AzureWebJobsStorage` value in the settings template is already configured to use it.

From the repository root:

```powershell
docker compose up -d azurite
```

Verify it is healthy:

```powershell
docker compose ps azurite
```

You should see `healthy` in the status column. Leave it running in the background while the function host is up.

To stop and wipe storage (e.g. between test runs):

```powershell
docker compose down -v
```

### 6. Start The Function Host

Run from the `functions/` folder:

```bash
cd functions
func start
```

Optional sanity check before `func start`:

```bash
python -c "import pydantic, langchain_core; print('deps ok')"
```

You should see the route:

```text
POST http://localhost:7071/api/inbox/external
```

### 7. Send A Test Request

PowerShell example:

```powershell
$body = @{
  url = "https://learn.microsoft.com/azure/azure-functions/functions-overview"
  my_note = "serverless overview"
} | ConvertTo-Json

Invoke-RestMethod \
  -Method Post \
  -Uri "http://localhost:7071/api/inbox/external" \
  -ContentType "application/json" \
  -Body $body
```

curl example:

```bash
curl -X POST "http://localhost:7071/api/inbox/external" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://learn.microsoft.com/azure/azure-functions/functions-overview","my_note":"serverless overview"}'
```

Expected success response shape:

```json
{
  "status": "indexed",
  "id": "...",
  "title": "...",
  "summary": "..."
}
```

### 8. Current MVP Behavior Note

- Dedup and persistence into Cosmos DB are still marked TODO in `functions/function_app.py`.
- So local run currently validates and executes extraction + processing + embedding, but does not yet upsert into Cosmos DB.

### 9. Troubleshooting

- `Process reporting unhealthy: Unable to access AzureWebJobsStorage`
  - Azurite is not running. Start it with `docker compose up -d azurite` from the repository root and wait for the `healthy` status before running `func start`.
- `func: command not found`
  - Install Azure Functions Core Tools v4 and restart terminal.
- `ModuleNotFoundError: semantic_search`
  - Ensure you run from an activated virtual environment and keep `src` import support from `functions/function_app.py`.
- `ModuleNotFoundError: pydantic` or `ModuleNotFoundError: langchain_core`
  - Install function dependencies explicitly: `python -m pip install -r functions/requirements.txt`.
- `func start` uses unexpected Python (for example global 3.13)
  - Activate `.venv` in the same terminal session before starting the host.
  - Confirm with `python --version` and `python -c "import sys; print(sys.executable)"`.
- Skill file not found
  - Verify `SKILLS_BACKEND=local` and `SKILLS_LOCAL_PATH=../skills` in `functions/local.settings.json`.
- 422 `extraction_failed`
  - Test with a simpler publicly accessible article URL first.
- 422 `processing_failed`
  - Check Anthropic key/model values and function host logs.

---

*This is a personal project and learning vehicle — for hands-on experience with LangChain, RAG patterns, Azure serverless, and agentic AI workflows.*
