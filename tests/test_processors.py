"""
Tests for document processors.
"""

import pytest
from semantic_search.processors import RawDocument, WebPageProcessor


# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta property="og:description" content="A test article about Python">
    <meta property="og:author" content="Test Author">
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
    </nav>
    
    <main>
        <article>
            <h1>Understanding Python Async/Await</h1>
            
            <p>Python's async/await syntax makes asynchronous programming much more intuitive. 
            Here's what you need to know.</p>
            
            <h2>Basic Concepts</h2>
            <p>Asynchronous programming allows your code to handle multiple tasks concurrently 
            without blocking execution.</p>
            
            <h3>Coroutines</h3>
            <p>A coroutine is a special function defined with <code>async def</code>:</p>
            
            <pre><code>async def fetch_data():
    await some_async_operation()
    return result</code></pre>
            
            <h2>Practical Examples</h2>
            <ul>
                <li>HTTP requests with aiohttp</li>
                <li>Database queries with asyncpg</li>
                <li>File I/O with aiofiles</li>
            </ul>
            
            <p>For more information, visit the 
            <a href="https://docs.python.org/3/library/asyncio.html">official documentation</a>.</p>
        </article>
    </main>
    
    <footer>
        <p>&copy; 2024 Test Site</p>
    </footer>
    
    <script>
        console.log("This should be removed");
    </script>
</body>
</html>
"""


class TestWebPageProcessor:
    """Tests for web page processing."""

    def test_basic_processing(self):
        """Test basic web page processing."""
        # Create raw document
        raw_doc = RawDocument(
            content=SAMPLE_HTML,
            source_type="web",
            url="https://example.com/article",
            metadata={"fetched_at": "2024-01-15T10:00:00Z"},
        )

        # Process
        processor = WebPageProcessor(include_enrichment=True)
        document = processor.process(raw_doc)

        # Verify basic attributes
        assert document.source_type == "web"
        assert document.url == "https://example.com/article"
        assert document.title is not None
        # Title should be extracted from <title> tag
        assert len(document.title) > 0

        # Verify content is markdown
        assert "# Understanding Python Async/Await" in document.content or "# Test Article" in document.content
        assert "## Basic Concepts" in document.content or "Basic Concepts" in document.content

        # Verify code blocks are preserved
        assert "async def" in document.content

        # Verify lists are converted
        assert "* HTTP requests" in document.content or "- HTTP requests" in document.content

        # Verify scripts/nav are removed
        assert "console.log" not in document.content
        assert "Home" not in document.content or "About" not in document.content

        print("\n=== Processed Document ===")
        print(f"Title: {document.title}")
        print(f"URL: {document.url}")
        print(f"\n=== Content ===\n{document.content[:500]}...")
        print(f"\n=== Metadata ===\n{document.metadata}")
        print(f"\n=== Statistics ===\n{document.statistics}")

    def test_metadata_extraction(self):
        """Test that metadata is properly extracted."""
        raw_doc = RawDocument(
            content=SAMPLE_HTML,
            source_type="web",
            url="https://example.com/article",
        )

        processor = WebPageProcessor(include_enrichment=True)
        document = processor.process(raw_doc)

        # Check metadata from HTML
        assert "author" in document.metadata or "og_title" in document.metadata
        assert "description" in document.metadata

    def test_statistics_calculation(self):
        """Test that statistics are correctly calculated."""
        raw_doc = RawDocument(
            content=SAMPLE_HTML,
            source_type="web",
        )

        processor = WebPageProcessor(include_enrichment=True)
        document = processor.process(raw_doc)

        # Verify statistics exist
        assert "character_count" in document.statistics
        assert "word_count" in document.statistics
        assert "reading_time_minutes" in document.statistics
        assert "heading_count" in document.statistics

        # Verify reasonable values
        assert document.statistics["character_count"] > 0
        assert document.statistics["word_count"] > 0
        assert document.statistics["reading_time_minutes"] >= 1

    def test_without_enrichment(self):
        """Test processing without enrichment."""
        raw_doc = RawDocument(
            content=SAMPLE_HTML,
            source_type="web",
        )

        processor = WebPageProcessor(include_enrichment=False)
        document = processor.process(raw_doc)

        # Should have content but no statistics
        assert len(document.content) > 0
        assert document.statistics == {}


if __name__ == "__main__":
    # Run a simple test manually
    test = TestWebPageProcessor()
    test.test_basic_processing()
