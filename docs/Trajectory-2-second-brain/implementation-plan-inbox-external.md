# Implementation Plan — External Inbox Pipeline (MVP)

**Scope:** `POST /api/inbox/external` — URL ingestion for external content  
**Milestone:** Working end-to-end: save URL → search by topic → get source back  
**Approach:** Agile — ship thin vertical slice first, iterate

---

## Step 0 — Extend the Data Model

Before writing pipeline code, define the storage contract.

**New Cosmos DB document type: `external`**

```python
# src/semantic_search/models_v2.py

class ExternalItem(BaseModel):
    id: str                        # sha256(url)[:16]
    type: Literal["external"]
    user_id: str

    title: str
    summary: str                   # 2-3 sentences, Claude-generated
    key_concepts: list[str]        # ["kubernetes", "autoscaling"]
    source_url: str
    source_type: str               # article | video | tweet | post | pdf
    saved_at: datetime
    my_note: str | None = None     # optional user annotation

    embedding: list[float]         # embed(summary + my_note)
    content_hash: str              # sha256(url) — dedup key
```

**Key difference from original chunk schema:** no `full_text`, no `chunks[]`, one embedding per item.

**Tasks:**
- [ ] Add `ExternalItem` Pydantic model
- [ ] Extend Cosmos DB container to accept both `external` and `note` types (same container, partition key `/userId`)
- [ ] Add vector index on `/embedding` for `external` type items

---

## Step 1 — Source Detector

**What:** Given a URL, determine `source_type` and which extractor to call.  
**How:** Deterministic URL pattern matching — no model involved.

```python
# src/semantic_search/sources/detector.py

class SourceType(str, Enum):
    ARTICLE  = "article"
    VIDEO    = "video"
    TWEET    = "tweet"
    TELEGRAM = "telegram_post"
    PDF      = "pdf"

def detect_source_type(url: str) -> SourceType:
    patterns = {
        SourceType.VIDEO:    [r"youtube\.com", r"youtu\.be"],
        SourceType.TWEET:    [r"twitter\.com", r"x\.com"],
        SourceType.TELEGRAM: [r"t\.me"],
        SourceType.PDF:      [r"\.pdf($|\?)"],
    }
    for source_type, regexes in patterns.items():
        if any(re.search(p, url) for p in regexes):
            return source_type
    return SourceType.ARTICLE  # default
```

**Tasks:**
- [ ] Implement `SourceDetector` with pattern matching
- [ ] Unit tests for URL patterns (edge cases: youtu.be shortlinks, t.me previews)

---

## Step 2 — Content Acquisition (code)

**What:** Fetch raw text from the URL. Source-type-specific code, no model.  
**How:** One extractor class per acquisition strategy, common interface.

```python
# src/semantic_search/sources/extractors.py

class ContentExtractor(ABC):
    @abstractmethod
    async def extract(self, url: str) -> RawContent:
        """Returns: { text: str, title: str | None, metadata: dict }"""
        pass

class ArticleExtractor(ContentExtractor):
    """HTTP fetch → existing WebPageProcessor. Covers ~90% of web by default."""
    # Reuses processors/web.py — no new code needed here

class YouTubeExtractor(ContentExtractor):
    """youtube-transcript-api → raw transcript text"""

class PDFExtractor(ContentExtractor):
    """Download + pypdf text extraction"""

class TweetExtractor(ContentExtractor):
    """Twitter/X oEmbed API (no auth needed for public tweets)"""

class TelegramExtractor(ContentExtractor):
    """t.me preview page scrape (public channels only)"""
```

**MVP scope — implement in this order:**
1. `ArticleExtractor` — reuses existing `WebPageProcessor`, effectively free,
   and immediately covers articles, blogs, docs, Substack, newsletters
2. `YouTubeExtractor` — high-value, common use case
3. `PDFExtractor` — research papers, reports
4. `TweetExtractor`, `TelegramExtractor` — later

**Tasks:**
- [ ] Define `ContentExtractor` ABC and `RawContent` model
- [ ] `ArticleExtractor` wrapping existing `WebPageProcessor`
- [ ] `YouTubeExtractor` using `youtube-transcript-api`
- [ ] `PDFExtractor` using `pypdf`
- [ ] Integration tests: real URLs, verify text quality

---

## Step 3 — Content Interpretation (skills + Sonnet)

**What:** Turn raw text into a structured memory item using a source-type-specific skill.  
**How:** Load skill from `skills/sources/{source_type}.md` → pass to Sonnet.

This is where extensibility lives. Adding a new source type (e.g. Substack, podcast) means creating a new skill file — no code change.

**Skill files** (stored in Azure Blob, loaded at runtime):

```
skills/sources/
├── article.md          ← default fallback
├── youtube.md          ← video transcript specifics
├── pdf.md              ← research papers, reports
├── tweet_thread.md     ← argument arc across thread
└── newsletter.md       ← digest format, key links
```

**Example: `skills/sources/article.md`**
```markdown
You are processing a saved web article for a personal knowledge base.

Extract:
- title: the article title (infer if not explicit)
- summary: 2-3 sentences capturing the core idea. Be specific — 
  specific enough to remind the user why they saved this.
- key_concepts: 3-8 lowercase keywords including both explicit 
  terms AND semantically related concepts useful for future search

If content is low-quality or empty: { "error": "insufficient_content" }
Respond ONLY with valid JSON, no markdown fences.
```

**Example: `skills/sources/youtube.md`**
```markdown
You are processing a YouTube video transcript for a personal knowledge base.

The input is raw auto-generated transcript — expect informal language, 
no punctuation, possible transcription errors.

Extract:
- title: infer from content if not provided
- summary: 2-3 sentences on the video's main argument or teaching
- key_concepts: 3-8 keywords; prefer the speaker's own terminology

If transcript is too short or uninformative: { "error": "insufficient_content" }
Respond ONLY with valid JSON, no markdown fences.
```

```python
# src/semantic_search/processing/external_processor.py

class ExternalProcessor:
    def __init__(self, llm: BaseChatModel, skills_loader: SkillsLoader):
        self.llm = llm
        self.skills_loader = skills_loader

    async def process(
        self, raw: RawContent, source_type: SourceType
    ) -> ProcessedContent:
        # Load source-specific skill, fall back to article.md
        skill = await self.skills_loader.load(
            f"sources/{source_type.value}.md",
            fallback="sources/article.md"
        )

        truncated = truncate_to_tokens(raw.text, max_tokens=4000)

        response = await self.llm.ainvoke([
            SystemMessage(content=skill),
            HumanMessage(content=truncated),
        ])

        return ProcessedContent(**json.loads(response.content))
```

```python
# src/semantic_search/processing/skills_loader.py

class SkillsLoader:
    """Loads skill files from local path (dev) or Azure Blob (prod).
    Controlled by SKILLS_BACKEND env var: 'local' | 'blob'
    """
    async def load(self, path: str, fallback: str | None = None) -> str:
        try:
            return await self._read(path)
        except NotFoundError:
            if fallback:
                return await self._read(fallback)
            raise
```

**Tasks:**
- [ ] `SkillsLoader` with local/Blob backends, env-var controlled
- [ ] Write `skills/sources/article.md` (Sprint 1)
- [ ] Write `skills/sources/youtube.md` (Sprint 2)
- [ ] `ExternalProcessor` with skill loading + fallback
- [ ] Handle `insufficient_content` error gracefully
- [ ] Test: verify different skill files produce meaningfully different summaries

---

## Step 4 — Embedding + Dedup

**What:** Generate one embedding per item. Skip if URL already indexed.  
**How:** LangChain embeddings + SHA-256 hash on URL as dedup key.

```python
# src/semantic_search/pipeline/embedder.py

class ExternalEmbedder:
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings  # LangChain interface

    def build_embed_text(self, item: ProcessedContent, my_note: str | None) -> str:
        """Combine summary + annotation for embedding."""
        parts = [item.summary]
        if my_note:
            parts.append(f"Note: {my_note}")
        return " ".join(parts)

    async def embed(self, item: ProcessedContent, my_note: str | None) -> list[float]:
        text = self.build_embed_text(item, my_note)
        return await self.embeddings.aembed_query(text)

    @staticmethod
    def url_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]
```

**Dedup check** (before extraction, saves API cost):
```python
existing = await cosmos.get_by_hash(url_hash)
if existing:
    return {"status": "duplicate", "id": existing.id}
```

**Tasks:**
- [ ] `ExternalEmbedder` class
- [ ] Dedup check at pipeline entry (hash on URL)
- [ ] LangChain embeddings config (OpenAI `text-embedding-3-small`)

---

## Step 5 — Azure Function Endpoint

**What:** HTTP trigger, ties all steps together.  
**Input:** `{ url: string, my_note?: string }`  
**Output:** `{ id, title, summary, status: "indexed" | "duplicate" }`

```python
# functions/inbox_external/__init__.py

@app.route(route="inbox/external", methods=["POST"])
async def inbox_external(req: HttpRequest) -> HttpResponse:
    body = req.get_json()
    url = body["url"]
    my_note = body.get("my_note")

    # 1. Dedup check
    url_hash = ExternalEmbedder.url_hash(url)
    if await vector_store.exists(url_hash):
        return ok({"status": "duplicate"})

    # 2. Detect source type
    source_type = detect_source_type(url)

    # 3. Extract raw content
    extractor = extractor_registry[source_type]
    raw = await extractor.extract(url)

    # 4. Process (Sonnet)
    processed = await processor.process(raw, source_type)
    if processed.error:
        return bad_request({"error": processed.error})

    # 5. Embed
    embedding = await embedder.embed(processed, my_note)

    # 6. Store
    item = ExternalItem(
        id=url_hash,
        source_url=url,
        source_type=source_type,
        my_note=my_note,
        embedding=embedding,
        **processed.dict(),
    )
    await vector_store.upsert(item)

    return ok({"status": "indexed", "id": item.id, "title": item.title})
```

**Tasks:**
- [ ] Azure Function HTTP trigger
- [ ] Request validation (URL format, max length)
- [ ] Error handling: extraction failed, model returned error, Cosmos DB timeout
- [ ] Local testing with `func start`

---

## Sprint 1 — What to Actually Build First

Start here — thin vertical slice, article URLs only:

```
Step 0  Data model + Cosmos DB schema         1 day
Step 1  SourceDetector (articles only)        0.5 day
Step 2  ArticleExtractor (wraps existing)     0.5 day
Step 3  ExternalProcessor + skill file        1 day
Step 4  ExternalEmbedder + dedup              1 day
Step 5  Azure Function endpoint               1 day
─────────────────────────────────────────────────────
                                    Total  ~5 days
```

**Definition of done for Sprint 1:**  
Send a URL of any article → get back title + summary → can find it via vector search by topic.

**Sprint 2 adds:** YouTube extractor, PDF extractor, Telegram bot interface.

---

## Open Questions (to resolve in Sprint 1)

1. **Skills storage location for local dev:** local `skills/` folder, swap to Azure Blob for production. One env var controls it.

2. **Token truncation strategy:** articles can be 20k+ tokens. Send first 4000 tokens to Sonnet — sufficient for summary extraction. YouTube transcripts: summarize in segments if >8000 tokens.

3. **What if extraction fails?** (paywalled article, JS-rendered page, private Telegram channel) — return `{ status: "extraction_failed", reason }`, store the URL + my_note only, no summary/embedding. User gets notified.

4. **Rate limiting on the endpoint:** for personal use, not needed in MVP. Add later if exposing to others.
