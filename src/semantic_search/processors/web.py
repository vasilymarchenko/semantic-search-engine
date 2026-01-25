"""
Web page processor for converting HTML to markdown.

Uses readability for main content extraction and markdownify for HTML → Markdown.
"""

import re
from datetime import datetime, UTC
from typing import Any

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from readability import Document as ReadabilityDocument

from semantic_search.processors.base import (
    Document,
    DocumentProcessor,
    Enricher,
    Normalizer,
    Parser,
    RawDocument,
)


class WebPageParser(Parser):
    """
    Parse HTML web pages and extract main content.

    Uses Mozilla's Readability algorithm to extract article content,
    removing navigation, ads, sidebars, and other boilerplate.
    """

    def parse(self, raw_doc: RawDocument) -> dict[str, Any]:
        """
        Parse HTML and extract main article content.

        Args:
            raw_doc: Raw HTML document

        Returns:
            Dictionary with cleaned HTML and metadata
        """
        html_content = (
            raw_doc.content
            if isinstance(raw_doc.content, str)
            else raw_doc.content.decode("utf-8", errors="ignore")
        )

        # Use Readability to extract main content
        doc = ReadabilityDocument(html_content)

        # Extract title
        title = doc.title()

        # Extract main content (already cleaned HTML)
        article_html = doc.summary()

        # Parse with BeautifulSoup for additional metadata
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract metadata from meta tags
        metadata = self._extract_metadata(soup)

        return {
            "title": title,
            "html": article_html,
            "metadata": metadata,
        }

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract metadata from HTML meta tags."""
        metadata = {}

        # OpenGraph tags
        og_title = soup.find("meta", property="og:title")
        if og_title:
            metadata["og_title"] = og_title.get("content", "")

        og_description = soup.find("meta", property="og:description")
        if og_description:
            metadata["description"] = og_description.get("content", "")

        og_author = soup.find("meta", property="og:author")
        if og_author:
            metadata["author"] = og_author.get("content", "")

        og_published = soup.find("meta", property="article:published_time")
        if og_published:
            metadata["published_date"] = og_published.get("content", "")

        # Twitter card tags (fallback)
        if "description" not in metadata:
            twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
            if twitter_desc:
                metadata["description"] = twitter_desc.get("content", "")

        # Standard meta tags (fallback)
        if "description" not in metadata:
            standard_desc = soup.find("meta", attrs={"name": "description"})
            if standard_desc:
                metadata["description"] = standard_desc.get("content", "")

        if "author" not in metadata:
            author_tag = soup.find("meta", attrs={"name": "author"})
            if author_tag:
                metadata["author"] = author_tag.get("content", "")

        return metadata


class WebPageNormalizer(Normalizer):
    """
    Convert HTML to clean markdown format.

    Uses markdownify with custom options for better markdown quality.
    """

    def __init__(
        self,
        heading_style: str = "ATX",
        bullets: str = "-",
        code_language: str = "",
        strip_tags: list[str] | None = None,
    ):
        """
        Initialize normalizer with markdown conversion options.

        Args:
            heading_style: "ATX" (# headers) or "SETEXT" (underlined)
            bullets: Character for unordered lists ("-", "*", "+")
            code_language: Default language for code blocks
            strip_tags: HTML tags to completely remove
        """
        self.heading_style = heading_style
        self.bullets = bullets
        self.code_language = code_language
        self.strip_tags = strip_tags or ["script", "style", "nav", "footer"]

    def normalize(self, parsed_data: dict[str, Any]) -> str:
        """
        Convert HTML to markdown.

        Args:
            parsed_data: Output from WebPageParser.parse()

        Returns:
            Clean markdown content
        """
        html = parsed_data["html"]
        title = parsed_data.get("title", "")

        # Remove unwanted tags
        soup = BeautifulSoup(html, "html.parser")
        for tag_name in self.strip_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Convert to markdown
        markdown = md(
            str(soup),
            heading_style=self.heading_style,
            bullets=self.bullets,
            code_language=self.code_language,
            strip=["script", "style"],
        )

        # Clean up excessive whitespace
        markdown = self._clean_whitespace(markdown)

        # Add title as H1 if present
        if title:
            markdown = f"# {title}\n\n{markdown}"

        return markdown

    def _clean_whitespace(self, text: str) -> str:
        """Clean excessive whitespace from markdown."""
        # Remove more than 2 consecutive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing whitespace from lines
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        # Remove leading/trailing whitespace
        text = text.strip()

        return text


class WebPageEnricher(Enricher):
    """
    Add computed metadata to web documents.

    Adds statistics like word count, reading time, and content classification.
    """

    def enrich(self, document: Document) -> Document:
        """
        Add enrichment metadata.

        Args:
            document: Document to enrich

        Returns:
            Document with statistics and classification
        """
        content = document.content

        # Calculate statistics
        char_count = len(content)
        word_count = len(content.split())
        reading_time_minutes = max(1, word_count // 200)  # ~200 words per minute

        # Count markdown elements
        heading_count = len(re.findall(r"^#{1,6}\s", content, re.MULTILINE))
        code_block_count = len(re.findall(r"```", content)) // 2
        link_count = len(re.findall(r"\[.*?\]\(.*?\)", content))

        # Detect language (simple heuristic for now)
        language = "en"  # Default to English (could use langdetect library)

        # Update statistics
        document.statistics = {
            "character_count": char_count,
            "word_count": word_count,
            "reading_time_minutes": reading_time_minutes,
            "heading_count": heading_count,
            "code_block_count": code_block_count,
            "link_count": link_count,
        }

        # Add enrichment metadata
        document.metadata["language"] = language
        document.metadata["processed_at"] = datetime.now(UTC).isoformat()

        return document


class WebPageProcessor(DocumentProcessor):
    """
    Complete processor for web pages.

    Combines Parser → Normalizer → Enricher for web content.
    """

    def __init__(self, include_enrichment: bool = True):
        """
        Initialize web page processor.

        Args:
            include_enrichment: Whether to add enrichment metadata
        """
        parser = WebPageParser()
        normalizer = WebPageNormalizer()
        enricher = WebPageEnricher() if include_enrichment else None

        super().__init__(parser, normalizer, enricher)
