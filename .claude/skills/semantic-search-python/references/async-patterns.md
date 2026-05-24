# Async Patterns Reference

**Python 3.11+ async — patterns specific to this project's pipeline architecture.**

---

## TaskGroup — Structured Concurrency (3.11+)

**Rule: prefer `TaskGroup` over `asyncio.gather()`.** The one exception — `gather()` is acceptable when a `Semaphore` already controls concurrency (see Semaphore section below), because the error-propagation trade-off is acceptable when the call site is a tight, bounded batch. In all other cases use `TaskGroup`.

Errors from any `TaskGroup` task cancel siblings and are re-raised as `ExceptionGroup`. Use for parallel work where all tasks must succeed.

```python
import asyncio

# ❌ gather() without Semaphore — errors are easy to lose, cancellation is messy
results = await asyncio.gather(
    embed(chunk1), embed(chunk2), embed(chunk3),
    return_exceptions=True,  # now you have to inspect each result manually
)

# ✅ TaskGroup — structured, all-or-nothing
async def embed_batch(chunks: list[Chunk]) -> list[list[float]]:
    results: list[list[float]] = [None] * len(chunks)  # type: ignore[list-item]

    async def embed_one(i: int, chunk: Chunk) -> None:
        results[i] = await embedder.embed(chunk.preview)

    async with asyncio.TaskGroup() as tg:
        for i, chunk in enumerate(chunks):
            tg.create_task(embed_one(i, chunk))

    return results  # all succeeded or we raised
```

### Handling ExceptionGroup from TaskGroup

```python
try:
    async with asyncio.TaskGroup() as tg:
        for chunk in chunks:
            tg.create_task(embed_and_store(chunk))
except* EmbeddingError as eg:
    # except* — Python 3.11, handles ExceptionGroup branches
    logger.error("Embedding failed for %d chunks", len(eg.exceptions))
    for exc in eg.exceptions:
        logger.error("  %s", exc)
    raise IngestionError("Batch embedding failed") from eg
except* httpx.TimeoutException as eg:
    raise IngestionError("Embedding API timed out") from eg
```

---

## Semaphore — Rate Limiting API Calls

Critical for the embedding pipeline: OpenAI has rate limits, Cosmos DB has RU limits.
Create the semaphore once per pipeline run, share across all coroutines.

```python
import asyncio

class EmbeddingPipeline:
    def __init__(self, settings: Settings) -> None:
        self._semaphore = asyncio.Semaphore(settings.embedding_concurrency)

    async def embed_chunk(self, chunk: Chunk) -> list[float]:
        async with self._semaphore:           # blocks if concurrency limit hit
            return await self._embedder.embed(chunk.preview)

    async def embed_all(self, chunks: list[Chunk]) -> list[list[float]]:
        # gather() is the stated exception to the TaskGroup-first rule:
        # Semaphore already bounds concurrency, and the flat batch makes
        # per-task error inspection acceptable at this call site.
        return await asyncio.gather(
            *(self.embed_chunk(c) for c in chunks)
        )
```

### Semaphore + TaskGroup (full pattern)

```python
async def ingest_documents(
    documents: list[Document],
    *,
    max_concurrent: int = 5,
) -> list[str]:
    """Returns IDs of successfully ingested documents."""
    sem = asyncio.Semaphore(max_concurrent)
    ingested_ids: list[str] = []

    async def ingest_one(doc: Document) -> None:
        async with sem:
            chunks = chunker.chunk(doc)
            embeddings = await embed_batch(chunks)
            await store.upsert(doc, chunks, embeddings)
            ingested_ids.append(doc.id)

    async with asyncio.TaskGroup() as tg:
        for doc in documents:
            tg.create_task(ingest_one(doc))

    return ingested_ids
```

---

## `asyncio.timeout()` — 3.11+ (replaces `asyncio.wait_for`)

```python
import asyncio

# ❌ Old
result = await asyncio.wait_for(connector.fetch(source_id), timeout=30.0)

# ✅ 3.11+
async with asyncio.timeout(30.0):
    result = await connector.fetch(source_id)

# With error handling
try:
    async with asyncio.timeout(30.0):
        result = await connector.fetch(source_id)
except TimeoutError:
    raise IngestionError(f"Connector timed out after 30s: {source_id}")
```

---

## Async Context Manager — Resource Lifecycle

Use for anything that needs setup/teardown: DB connections, HTTP sessions, API clients.

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def cosmos_client(settings: Settings) -> AsyncGenerator[CosmosClient, None]:
    client = CosmosClient(
        url=settings.cosmos_endpoint,
        credential=settings.cosmos_key.get_secret_value(),
    )
    try:
        yield client
    finally:
        await client.close()

# Usage
async with cosmos_client(settings) as client:
    container = client.get_database_client(settings.cosmos_database)
    await container.upsert_item(doc.model_dump(by_alias=True, exclude_none=True))
```

### Class-based async context manager

```python
class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: CosmosClient | None = None

    async def __aenter__(self) -> VectorStore:
        self._client = CosmosClient(
            url=self._settings.cosmos_endpoint,
            credential=self._settings.cosmos_key.get_secret_value(),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def upsert_document(self, document: Document) -> None:
        assert self._client is not None, "Use VectorStore as async context manager"
        ...

# Usage
async with VectorStore(settings) as store:
    await store.upsert_document(doc)
```

---

## Async Generator — Streaming Large Collections

For connectors fetching many documents: yield as you go, don't buffer everything.

```python
from collections.abc import AsyncGenerator

class TelegramConnector:
    async def stream(self, channel_id: str) -> AsyncGenerator[RawDocument, None]:
        async for message in self._client.get_messages(channel_id, limit=None):
            yield RawDocument(
                source_type="telegram",
                source_id=str(message.id),
                content=message.text or "",
                content_type="text",
                metadata={"channel": channel_id, "date": message.date.isoformat()},
            )

# Consuming
async for raw_doc in connector.stream("my_channel"):
    document = await processor.process(raw_doc)
    await store.upsert_document(document)
```

---

## Retry with Exponential Backoff

For flaky external APIs (Telegram MTProto, OpenAI, Cosmos DB throttling):

```python
import asyncio
import random
from collections.abc import Callable, Awaitable
from typing import TypeVar

T = TypeVar("T")

async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except retryable as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            logger.warning(
                "Attempt %d/%d failed, retrying in %.1fs: %s",
                attempt + 1, max_attempts, delay + jitter, exc,
            )
            await asyncio.sleep(delay + jitter)
    raise last_exc  # type: ignore[misc]

# Usage
result = await with_retry(
    lambda: embedder.embed(text),
    max_attempts=3,
    retryable=(httpx.TimeoutException, EmbeddingError),
)
```

---

## Azure Functions Async Entry Point

Azure Functions supports async handlers directly — always use them:

```python
import azure.functions as func
import logging

app = func.FunctionApp()
logger = logging.getLogger(__name__)

@app.function_name("IndexDocument")
@app.queue_trigger(
    arg_name="msg",
    queue_name="indexing-queue",
    connection="AzureWebJobsStorage",
)
async def index_document(msg: func.QueueMessage) -> None:
    """Azure Function — async queue trigger for document ingestion."""
    payload = msg.get_json()
    source_type = payload["source_type"]
    source_id = payload["source_id"]

    logger.info("Indexing %s/%s", source_type, source_id)

    connector = ConnectorRegistry.get(source_type)(settings)

    async with VectorStore(settings) as store:
        async with asyncio.timeout(120.0):
            raw_docs = await connector.fetch(source_id)
            for raw in raw_docs:
                doc = await processor.process(raw)
                chunks = chunker.chunk(doc)
                await pipeline.embed_and_store(doc, chunks, store)
```
