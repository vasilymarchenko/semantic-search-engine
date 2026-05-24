"""
Embedding generation for the external inbox pipeline.

One embedding per external item — target text is summary + key_concepts + my_note.
URL-hash dedup check happens before extraction to save API cost.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from semantic_search.models_v2 import ProcessedContent, url_hash


class ExternalEmbedder:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings

    async def embed(self, processed: ProcessedContent, my_note: str | None) -> list[float]:
        """Generate a single embedding for a processed external item."""
        text = _build_embed_text(processed, my_note)
        return await self._embeddings.aembed_query(text)

    @staticmethod
    def item_id(source_url: str) -> str:
        """Stable dedup key and Cosmos DB document id — SHA-256 of the URL."""
        return url_hash(source_url)


def _build_embed_text(processed: ProcessedContent, my_note: str | None) -> str:
    parts = [processed.summary]
    if processed.key_concepts:
        parts.append(" ".join(processed.key_concepts))
    if my_note:
        parts.append(f"Note: {my_note}")
    return " ".join(filter(None, parts))
