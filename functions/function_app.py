"""
Azure Functions v2 app — POST /api/inbox/external

Orchestrates the full external ingestion pipeline:
  URL → dedup check → source detection → content extraction
      → LLM interpretation → embedding → Cosmos DB upsert
"""

from __future__ import annotations

import json
import logging

import azure.functions as func

from semantic_search.config import settings
from semantic_search.models_v2 import ExternalItem
from semantic_search.pipeline.embedder import ExternalEmbedder
from semantic_search.processing.external_processor import ExternalProcessor
from semantic_search.processing.skills_loader import SkillsLoader
from semantic_search.sources.detector import detect_source_type
from semantic_search.sources.extractors import get_extractor

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ---------------------------------------------------------------------------
# Module-level singletons — constructed once per cold start
# ---------------------------------------------------------------------------

_skills_loader = SkillsLoader(
    backend=settings.skills_backend,
    local_path=settings.skills_local_path,
    blob_connection=settings.skills_blob_connection,
    blob_container=settings.skills_blob_container,
)


def _build_processor() -> ExternalProcessor:
    from langchain_anthropic import ChatAnthropic  # type: ignore[import-untyped]

    llm = ChatAnthropic(
        model=settings.processor_model,
        api_key=settings.anthropic_api_key.get_secret_value(),
    )
    return ExternalProcessor(llm=llm, skills_loader=_skills_loader)


def _build_embedder() -> ExternalEmbedder:
    from langchain_openai import OpenAIEmbeddings  # type: ignore[import-untyped]

    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    return ExternalEmbedder(embeddings=embeddings)


_processor: ExternalProcessor | None = None
_embedder: ExternalEmbedder | None = None


def _get_processor() -> ExternalProcessor:
    global _processor
    if _processor is None:
        _processor = _build_processor()
    return _processor


def _get_embedder() -> ExternalEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = _build_embedder()
    return _embedder


# ---------------------------------------------------------------------------
# HTTP trigger
# ---------------------------------------------------------------------------


@app.route(route="inbox/external", methods=["POST"])
async def inbox_external(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ingest a URL into the personal knowledge base.

    Request body (JSON):
        { "url": "https://...", "my_note": "optional annotation" }

    Response (JSON):
        200 { "status": "indexed",   "id": "...", "title": "...", "summary": "..." }
        200 { "status": "duplicate", "id": "..." }
        400 { "error": "<validation message>" }
        422 { "status": "extraction_failed" | "processing_failed", "reason": "..." }
    """
    # --- Input validation ---
    try:
        body = req.get_json()
    except ValueError:
        return _bad_request("Request body must be valid JSON.")

    url: str = body.get("url", "")
    if not url:
        return _bad_request("'url' field is required.")
    if not url.startswith(("http://", "https://")):
        return _bad_request("'url' must be an absolute HTTP or HTTPS URL.")
    if len(url) > 2048:
        return _bad_request("'url' exceeds maximum length of 2048 characters.")

    my_note: str | None = body.get("my_note") or None

    # --- Dedup check ---
    item_id = ExternalEmbedder.item_id(url)
    # TODO: check Cosmos DB — if item with id == item_id exists, return duplicate
    # existing = await _cosmos_container().read_item(item_id, partition_key="default")
    # if existing: return _ok({"status": "duplicate", "id": item_id})

    # --- Source detection ---
    source_type = detect_source_type(url)
    logger.info("source_type=%s url=%s", source_type, url)

    # --- Content acquisition ---
    extractor = get_extractor(source_type)
    try:
        raw = await extractor.extract(url)
    except Exception:
        logger.exception("Extraction failed for %s", url)
        return _unprocessable({"status": "extraction_failed", "reason": "fetch_error"})

    if not raw.text.strip():
        return _unprocessable({"status": "extraction_failed", "reason": "empty_content"})

    # --- LLM interpretation ---
    processor = _get_processor()
    processed = await processor.process(raw, source_type)

    if processed.error:
        return _unprocessable({"status": "processing_failed", "reason": processed.error})

    # --- Embedding ---
    embedder = _get_embedder()
    embedding = await embedder.embed(processed, my_note)

    # --- Construct item ---
    item = ExternalItem.build(
        url=url,
        user_id="default",  # single-user MVP; extend with auth later
        processed=processed,
        source_type=source_type,
        embedding=embedding,
        my_note=my_note,
    )

    # --- Store ---
    # TODO: await _cosmos_container().upsert_item(item.model_dump(exclude={"embedding"}))
    # TODO: store embedding in vector index
    logger.info("Indexed id=%s title=%r", item.id, item.title)

    return _ok(
        {
            "status": "indexed",
            "id": item.id,
            "title": item.title,
            "summary": item.summary,
        }
    )


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(data: dict) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data), mimetype="application/json", status_code=200
    )


def _bad_request(message: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}), mimetype="application/json", status_code=400
    )


def _unprocessable(data: dict) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data), mimetype="application/json", status_code=422
    )
