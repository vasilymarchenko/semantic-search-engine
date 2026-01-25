"""
Ingestion CLI - Complete pipeline from source to chunks.

This CLI handles the full ingestion pipeline:
1. Load content (URL or file)
2. Process to normalized markdown (DocumentProcessor)
3. Chunk the markdown (MarkdownChunker)
4. Save results to output directory

Usage:
    ingestion-cli https://example.com/article
    ingestion-cli document.html
    ingestion-cli document.md
"""

import argparse
import asyncio
import re
import shutil
import sys
from pathlib import Path

from semantic_search.chunking.markdown import MarkdownChunker
from semantic_search.processors import RawDocument, WebPageProcessor
from semantic_search.utils.fetcher import (
    detect_file_format,
    detect_source_type,
    fetch_url,
    generate_output_name,
)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_section(text: str) -> None:
    """Print a formatted section header."""
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)


async def load_from_url(url: str) -> RawDocument:
    """Load content from URL."""
    print(f"🌐 Fetching URL: {url}")
    try:
        raw_doc = await fetch_url(url)
        print(f"✅ Fetched {raw_doc.metadata.get('content_length', 0)} bytes")
        return raw_doc
    except Exception as e:
        print(f"❌ Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)


def load_from_file(file_path: Path) -> RawDocument:
    """Load content from file."""
    print(f"📄 Reading file: {file_path}")

    # Detect format
    file_format = detect_file_format(file_path)

    if file_format == "pdf":
        print("❌ PDF format not yet supported", file=sys.stderr)
        sys.exit(1)
    elif file_format == "unknown":
        print(
            f"❌ Unsupported file format: {file_path.suffix}",
            file=sys.stderr,
        )
        print("Supported formats: .html, .htm, .md, .markdown", file=sys.stderr)
        sys.exit(1)

    # Read file
    try:
        content = file_path.read_text(encoding="utf-8")
        print(f"✅ Loaded {len(content)} characters")
    except Exception as e:
        print(f"❌ Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine source type
    if file_format == "html":
        source_type = "web"
    else:
        source_type = "markdown"

    return RawDocument(
        content=content,
        source_type=source_type,
        url=str(file_path),
        metadata={"file_format": file_format},
    )


def enrich_markdown(markdown: str, source_url: str) -> tuple[dict, dict]:
    """
    Add lightweight enrichment to markdown (stats and title extraction).
    
    Returns:
        Tuple of (metadata, statistics)
    """
    # Extract title (first H1 or derive from filename)
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1) if title_match else Path(source_url).stem
    
    # Calculate statistics
    char_count = len(markdown)
    word_count = len(markdown.split())
    reading_time = max(1, word_count // 200)  # ~200 words per minute
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


def process_document(raw_doc: RawDocument) -> tuple[str, dict, dict]:
    """
    Process raw document to normalized markdown.

    Returns:
        Tuple of (markdown_content, metadata, statistics)
    """
    if raw_doc.source_type == "web":
        print("🔄 Processing HTML to markdown...")
        processor = WebPageProcessor(include_enrichment=True)
        document = processor.process(raw_doc)
        print(f"✅ Processed: {document.title or 'Untitled'}")
        return document.content, document.metadata, document.statistics
    elif raw_doc.source_type == "markdown":
        print("🔄 Enriching markdown...")
        metadata, statistics = enrich_markdown(raw_doc.content, raw_doc.url or "")
        metadata.update(raw_doc.metadata)
        print(f"✅ Enriched: {metadata.get('title', 'Untitled')}")
        return raw_doc.content, metadata, statistics
    else:
        print(f"❌ Unsupported source type: {raw_doc.source_type}", file=sys.stderr)
        sys.exit(1)


def chunk_markdown(
    markdown: str, max_tokens: int, overlap_tokens: int, min_tokens: int
) -> list:
    """Chunk markdown content."""
    print(f"✂️  Chunking markdown (max={max_tokens}, overlap={overlap_tokens})...")

    chunker = MarkdownChunker(
        token_threshold=max_tokens + 200,  # Allow some buffer before chunking
        max_chunk_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        min_chunk_tokens=min_tokens,
    )

    chunks = chunker.chunk_document(markdown)
    print(f"✅ Created {len(chunks)} chunks")

    return chunks


def save_output(
    output_dir: Path,
    source: str,
    source_type: str,
    markdown: str,
    chunks: list,
    metadata: dict,
    statistics: dict,
) -> None:
    """Save normalized markdown and chunks to output directory."""
    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output name
    base_name = generate_output_name(source, source_type)

    # Save normalized markdown
    doc_file = output_dir / f"{base_name}.md"
    doc_file.write_text(markdown, encoding="utf-8")
    print(f"💾 Saved document: {doc_file}")

    # Save chunks
    for i, chunk in enumerate(chunks, start=1):
        chunk_file = output_dir / f"chunk_{i}.md"
        chunk_file.write_text(chunk.text, encoding="utf-8")

    print(f"💾 Saved {len(chunks)} chunks: chunk_1.md to chunk_{len(chunks)}.md")

    # Save metadata (optional, for debugging)
    if metadata or statistics:
        import json

        meta_file = output_dir / "metadata.json"
        meta_data = {
            "source": source,
            "source_type": source_type,
            "metadata": metadata,
            "statistics": statistics,
        }
        meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
        print(f"💾 Saved metadata: {meta_file}")


def print_verbose_info(chunks: list) -> None:
    """Print verbose chunk information for debugging."""  
    print_section("🔍 DETAILED CHUNK INFORMATION")
    
    # Show first 3 chunks in detail
    for i, chunk in enumerate(chunks[:3], start=1):
        print(f"\n--- Chunk {i} ---")
        print(f"Section: {' > '.join(chunk.section_path)}")
        print(f"Tokens: {chunk.token_count}")
        print(f"Offset: {chunk.start_offset}-{chunk.end_offset}")
        print(f"Content types: {[ct.value for ct in chunk.content_types]}")
        if chunk.metadata:
            print(f"Metadata: {chunk.metadata}")
        
        # Show text preview
        preview = chunk.text[:200].replace("\n", "\n  ")
        print(f"\nText preview (first 200 chars):")
        print(f"  {preview}")
        if len(chunk.text) > 200:
            print("  ...")
    
    if len(chunks) > 3:
        print(f"\n... and {len(chunks) - 3} more chunks")
    
    # Code block preservation check
    code_chunks = [c for c in chunks if c.metadata.get("has_code")]
    if code_chunks:
        print("\n" + "-" * 80)
        print(f"CODE BLOCK PRESERVATION CHECK")
        print("-" * 80)
        print(f"✅ Chunks with code blocks: {len(code_chunks)}")
        
        for i, chunk in enumerate(code_chunks[:3], start=1):
            delimiters = chunk.text.count("```")
            is_closed = delimiters % 2 == 0
            status = "✅ Properly closed" if is_closed else "❌ BROKEN!"
            print(f"  Chunk {i}: {delimiters} delimiters (```) - {status}")


def print_summary(markdown: str, chunks: list, metadata: dict, statistics: dict) -> None:
    """Print summary of results."""
    print_section("📊 SUMMARY")

    # Document info
    if statistics:
        print(f"Document: {statistics.get('word_count', 0)} words, "
              f"{statistics.get('character_count', 0)} characters")
        if "reading_time_minutes" in statistics:
            print(f"Reading time: {statistics['reading_time_minutes']} min")

    # Chunk info
    total_tokens = sum(c.token_count for c in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    min_tokens = min(c.token_count for c in chunks) if chunks else 0
    max_tokens = max(c.token_count for c in chunks) if chunks else 0

    print(f"\nChunks: {len(chunks)} total")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg tokens: {avg_tokens:.0f}")
    print(f"  Min tokens: {min_tokens}")
    print(f"  Max tokens: {max_tokens}")

    # Token distribution
    ranges = [
        (0, 200, "Very small"),
        (200, 400, "Optimal"),
        (400, 600, "Large"),
        (600, 1000, "Very large"),
    ]

    print("\n📈 Token distribution:")
    for min_t, max_t, label in ranges:
        count = sum(1 for c in chunks if min_t <= c.token_count < max_t)
        if count > 0:
            percentage = (count / len(chunks)) * 100
            print(f"  {label:12s}: {count:2d} chunks ({percentage:5.1f}%)")


async def async_main(args: argparse.Namespace) -> None:
    """Async main function."""
    print_header("🚀 INGESTION PIPELINE")

    # Step 1: Detect source type
    source_type = detect_source_type(args.source)
    print(f"📍 Source type: {source_type}")

    # Step 2: Load content
    print_section("📥 STEP 1: LOAD CONTENT")
    if source_type == "url":
        raw_doc = await load_from_url(args.source)
    else:
        file_path = Path(args.source)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        raw_doc = load_from_file(file_path)

    # Step 3: Process to markdown
    print_section("🔄 STEP 2: PROCESS TO MARKDOWN")
    markdown, metadata, statistics = process_document(raw_doc)

    # Step 4: Chunk markdown
    print_section("✂️  STEP 3: CHUNK MARKDOWN")
    chunks = chunk_markdown(
        markdown, args.max_tokens, args.overlap_tokens, args.min_tokens
    )

    # Step 5: Save output
    print_section("💾 STEP 4: SAVE OUTPUT")
    output_dir = Path(args.output_dir)
    save_output(
        output_dir, args.source, source_type, markdown, chunks, metadata, statistics
    )

    # Print summary
    print_summary(markdown, chunks, metadata, statistics)
    
    # Print verbose info if requested
    if args.verbose:
        print_verbose_info(chunks)

    print_header("✅ INGESTION COMPLETE")
    print(f"\n📂 Output directory: {output_dir.absolute()}")
    print("\n🔄 Next steps:")
    print("  1. Review the normalized markdown document")
    print("  2. Check the chunks for quality")
    print("  3. Next phase: Generate embeddings and index to vector store")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingestion pipeline: Load, process, and chunk content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ingestion-cli https://example.com/article
  ingestion-cli document.html
  ingestion-cli document.md
  ingestion-cli https://fastapi.tiangolo.com/ --max-tokens 600
        """,
    )

    parser.add_argument(
        "source",
        help="URL or file path (supported: .html, .htm, .md, .markdown)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="ingestion_output",
        help="Output directory (default: ingestion_output/)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=400,
        help="Maximum tokens per chunk (default: 400)",
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=50,
        help="Token overlap between chunks (default: 50)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=100,
        help="Minimum tokens per chunk (default: 100)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed chunk information and diagnostics",
    )

    args = parser.parse_args()

    # Run async main
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
