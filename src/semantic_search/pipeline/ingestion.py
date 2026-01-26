"""Ingestion service (load -> process -> chunk -> optional save).

This is the core service layer used by the CLI today and intended to be reused
by a future Azure Function/API.

No Rich/printing here: return structured results and raise exceptions.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from semantic_search.chunking.markdown import MarkdownChunker
from semantic_search.processors import Document, RawDocument, WebPageProcessor
from semantic_search.utils.fetcher import (
    detect_file_format,
    detect_source_type,
    fetch_url,
    generate_output_name,
)


class IngestionOptions(BaseModel):
    output_dir: Path = Path("ingestion_output")
    max_tokens: int = 400
    overlap_tokens: int = 50
    min_tokens: int = 100
    save_outputs: bool = False
    overwrite_output_dir: bool = True


class IngestionResult(BaseModel):
    source: str
    source_type: Literal["url", "file"]

    raw_document: RawDocument
    document: Document

    chunks: list[Any]

    output_dir: Path | None = None
    output_basename: str | None = None
    saved_files: dict[str, str] = Field(default_factory=dict)


class IngestionService:
    def __init__(self) -> None:
        self.web_processor = WebPageProcessor(include_enrichment=True)

    async def ingest(self, source: str, options: IngestionOptions) -> IngestionResult:
        source_type = detect_source_type(source)
        raw_document = await self._load(source, source_type)
        document = self._process(raw_document)

        chunker = MarkdownChunker(
            token_threshold=options.max_tokens + 200,
            max_chunk_tokens=options.max_tokens,
            overlap_tokens=options.overlap_tokens,
            min_chunk_tokens=options.min_tokens,
        )
        chunks = chunker.chunk_document(document.content)

        result = IngestionResult(
            source=source,
            source_type=source_type,
            raw_document=raw_document,
            document=document,
            chunks=chunks,
        )

        if options.save_outputs:
            self._save_outputs(result, options)

        return result

    async def _load(self, source: str, source_type: Literal["url", "file"]) -> RawDocument:
        if source_type == "url":
            return await fetch_url(source)

        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        file_format = detect_file_format(file_path)
        if file_format == "pdf":
            raise ValueError("PDF format not yet supported")
        if file_format == "unknown":
            raise ValueError(
                f"Unsupported file format: {file_path.suffix}. Supported: .html, .htm, .md, .markdown"
            )

        content = file_path.read_text(encoding="utf-8")
        raw_source_type = "web" if file_format == "html" else "markdown"

        return RawDocument(
            content=content,
            source_type=raw_source_type,
            url=str(file_path),
            metadata={"file_format": file_format},
        )

    def _process(self, raw_document: RawDocument) -> Document:
        if raw_document.source_type == "web":
            return self.web_processor.process(raw_document)

        if raw_document.source_type == "markdown":
            metadata, statistics = self._enrich_markdown(
                str(raw_document.content), raw_document.url or ""
            )
            metadata.update(raw_document.metadata)
            return Document(
                content=str(raw_document.content),
                source_type=raw_document.source_type,
                url=raw_document.url,
                title=metadata.get("title"),
                metadata=metadata,
                statistics=statistics,
            )

        raise ValueError(f"Unsupported source type: {raw_document.source_type}")

    def _enrich_markdown(self, markdown: str, source_url: str) -> tuple[dict, dict]:
        title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        title = title_match.group(1) if title_match else Path(source_url).stem

        char_count = len(markdown)
        word_count = len(markdown.split())
        reading_time = max(1, word_count // 200)
        heading_count = len(re.findall(r"^#{1,6}\s", markdown, re.MULTILINE))
        code_block_count = len(re.findall(r"```", markdown)) // 2
        link_count = len(re.findall(r"\[.*?\]\(.*?\)", markdown))

        metadata = {"title": title}
        statistics = {
            "character_count": char_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time,
            "heading_count": heading_count,
            "code_block_count": code_block_count,
            "link_count": link_count,
        }

        return metadata, statistics

    def _save_outputs(self, result: IngestionResult, options: IngestionOptions) -> None:
        output_dir = options.output_dir

        if output_dir.exists() and options.overwrite_output_dir:
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_basename = generate_output_name(result.source, result.source_type)

        # Document
        doc_path = output_dir / f"{output_basename}.md"
        doc_path.write_text(result.document.content, encoding="utf-8")

        # Chunks
        for i, chunk in enumerate(result.chunks, start=1):
            (output_dir / f"chunk_{i}.md").write_text(chunk.text, encoding="utf-8")

        # Metadata
        meta_path = output_dir / "metadata.json"
        meta_payload = {
            "source": result.source,
            "source_type": result.source_type,
            "metadata": result.document.metadata,
            "statistics": result.document.statistics,
        }
        meta_path.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")

        result.output_dir = output_dir
        result.output_basename = output_basename
        result.saved_files = {
            "document": str(doc_path),
            "metadata": str(meta_path),
            "chunks_dir": str(output_dir),
        }
