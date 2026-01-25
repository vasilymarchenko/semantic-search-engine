"""
Base classes and abstractions for document processing.

The document processing pipeline follows a three-stage pattern:
1. Parser: Extract raw content and metadata from source format
2. Normalizer: Convert to standardized markdown format
3. Enricher: Add computed metadata (language, stats, etc.)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """
    Raw document as received from a source connector.

    This represents the unprocessed input before any transformation.
    """

    content: str | bytes
    """Raw content (text, HTML, binary data)"""

    source_type: str
    """Source type (e.g., 'web', 'email', 'pdf')"""

    url: str | None = None
    """Original URL or source identifier"""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Source-specific metadata (author, timestamp, etc.)"""


class Document(BaseModel):
    """
    Normalized document in markdown format.

    This is the output of the document processor, ready for chunking.
    """

    content: str
    """Document content in markdown format"""

    source_type: str
    """Source type (e.g., 'web', 'email', 'pdf')"""

    url: str | None = None
    """Original URL or source identifier"""

    title: str | None = None
    """Document title (extracted or inferred)"""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Combined metadata from source + enrichment"""

    statistics: dict[str, Any] = Field(default_factory=dict)
    """Computed statistics (character count, word count, etc.)"""


class Parser(ABC):
    """
    Extract structured content from raw format.

    Responsibilities:
    - Parse source-specific format (HTML, email MIME, PDF)
    - Extract basic metadata (title, author, date)
    - Clean up malformed content
    """

    @abstractmethod
    def parse(self, raw_doc: RawDocument) -> dict[str, Any]:
        """
        Parse raw document and extract structured data.

        Args:
            raw_doc: Raw document to parse

        Returns:
            Dictionary with parsed content and metadata
        """
        pass


class Normalizer(ABC):
    """
    Convert parsed content to standardized markdown format.

    Responsibilities:
    - Transform HTML/rich text to markdown
    - Preserve document structure (headings, lists, code blocks)
    - Handle edge cases (nested structures, malformed markup)
    """

    @abstractmethod
    def normalize(self, parsed_data: dict[str, Any]) -> str:
        """
        Convert parsed data to markdown format.

        Args:
            parsed_data: Output from Parser.parse()

        Returns:
            Document content in markdown format
        """
        pass


class Enricher(ABC):
    """
    Add computed metadata to documents.

    Responsibilities:
    - Language detection
    - Document statistics (character/word count, reading time)
    - Content classification (article, tutorial, reference)
    """

    @abstractmethod
    def enrich(self, document: Document) -> Document:
        """
        Add enrichment metadata to document.

        Args:
            document: Document to enrich

        Returns:
            Document with additional metadata
        """
        pass


class DocumentProcessor(ABC):
    """
    Orchestrate the full processing pipeline.

    Combines Parser → Normalizer → Enricher into a single operation.
    """

    def __init__(
        self, parser: Parser, normalizer: Normalizer, enricher: Enricher | None = None
    ):
        """
        Initialize document processor.

        Args:
            parser: Parser for extracting content
            normalizer: Normalizer for markdown conversion
            enricher: Optional enricher for metadata
        """
        self.parser = parser
        self.normalizer = normalizer
        self.enricher = enricher

    def process(self, raw_doc: RawDocument) -> Document:
        """
        Process raw document through full pipeline.

        Args:
            raw_doc: Raw document from source connector

        Returns:
            Normalized document ready for chunking
        """
        # Stage 1: Parse
        parsed_data = self.parser.parse(raw_doc)

        # Stage 2: Normalize to markdown
        markdown_content = self.normalizer.normalize(parsed_data)

        # Create document
        document = Document(
            content=markdown_content,
            source_type=raw_doc.source_type,
            url=raw_doc.url,
            title=parsed_data.get("title"),
            metadata={
                **raw_doc.metadata,
                **parsed_data.get("metadata", {}),
            },
        )

        # Stage 3: Enrich (optional)
        if self.enricher:
            document = self.enricher.enrich(document)

        return document
