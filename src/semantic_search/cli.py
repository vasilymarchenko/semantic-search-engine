"""
Command-line interface for testing chunking strategies.

The command 'semantic-chunker' is registered in pyproject.toml:
    [project.scripts]
    semantic-chunker = "semantic_search.cli:main"

This creates an executable that calls the main() function below.
Multiple CLI commands can be defined by adding more entries to [project.scripts].
"""

import argparse
import shutil
import sys
from pathlib import Path

from semantic_search.chunking.markdown import MarkdownChunker


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test markdown chunking strategy on documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  semantic-chunker                                    # Use default document
  semantic-chunker path\\to\\document.md              # Chunk specific file
  semantic-chunker document.md --max-tokens 500       # Custom chunk size
  semantic-chunker --save -v                          # Save chunks to files
        """,
    )

    # Default path: project_root/docs/semantic-search-engine-plan.md
    default_doc = Path(__file__).parent.parent.parent / "docs" / "semantic-search-engine-plan.md"

    parser.add_argument(
        "document",
        nargs="?",
        default=str(default_doc),
        help="Path to markdown document (default: semantic-search-engine-plan.md)",
    )
    parser.add_argument(
        "--token-threshold",
        type=int,
        default=600,
        help="Document size threshold for chunking (default: 600)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=400,
        help="Maximum tokens per chunk (default: 400)",
    )
    parser.add_argument(
        "--overlap",
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
        help="Show detailed chunk information",
    )
    parser.add_argument(
        "--save",
        "-s",
        action="store_true",
        help="Save chunks to output folder (chunks_output/)",
    )

    args = parser.parse_args()

    # Validate file exists
    doc_path = Path(args.document)
    if not doc_path.exists():
        print(f"❌ Error: File not found: {doc_path}", file=sys.stderr)
        sys.exit(1)

    # Read document
    print("=" * 80)
    print("MARKDOWN CHUNKING STRATEGY TEST")
    print("=" * 80)
    print(f"\nDocument: {doc_path}")
    print(f"Configuration:")
    print(f"  Token threshold: {args.token_threshold}")
    print(f"  Max chunk tokens: {args.max_tokens}")
    print(f"  Overlap tokens: {args.overlap}")
    print(f"  Min chunk tokens: {args.min_tokens}\n")

    try:
        markdown_text = doc_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize chunker
    chunker = MarkdownChunker(
        token_threshold=args.token_threshold,
        max_chunk_tokens=args.max_tokens,
        overlap_tokens=args.overlap,
        min_chunk_tokens=args.min_tokens,
    )

    # Chunk the document
    print("=" * 80)
    print("CHUNKING RESULTS")
    print("=" * 80)

    chunks = chunker.chunk_document(markdown_text)

    # Save chunks to files if requested
    if args.save:
        output_dir = Path("chunks_output")
        
        # Clean output directory
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save each chunk
        for i, chunk in enumerate(chunks, start=1):
            chunk_file = output_dir / f"{i}.md"
            chunk_file.write_text(chunk.text, encoding="utf-8")
        
        print(f"\n💾 Saved {len(chunks)} chunks to {output_dir.absolute()}\\")

    # Summary statistics
    total_tokens = sum(c.token_count for c in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0

    print(f"\n✅ Created {len(chunks)} chunks")
    print(f"📊 Total tokens: {total_tokens}")
    print(f"📊 Average chunk size: {avg_tokens:.0f} tokens")
    print(f"📊 Min chunk size: {min(c.token_count for c in chunks)} tokens")
    print(f"📊 Max chunk size: {max(c.token_count for c in chunks)} tokens")

    # Check for oversized chunks
    oversized = [c for c in chunks if c.metadata.get("oversized")]
    if oversized:
        print(f"\n⚠️  Oversized chunks: {len(oversized)}")
        for chunk in oversized:
            print(f"    - {chunk.token_count} tokens: {chunk.metadata.get('reason')}")

    # Token distribution
    print(f"\n📈 Token distribution:")
    ranges = [
        (0, 200, "Very small"),
        (200, 400, "Optimal"),
        (400, 600, "Large"),
        (600, 1000, "Very large"),
        (1000, float("inf"), "Oversized"),
    ]

    for min_t, max_t, label in ranges:
        count = sum(1 for c in chunks if min_t <= c.token_count < max_t)
        if count > 0:
            percentage = (count / len(chunks)) * 100
            print(
                f"  {label:12s} ({min_t:4d}-{max_t:4.0f} tokens): "
                f"{count:2d} chunks ({percentage:5.1f}%)"
            )

    # Detailed chunk information (if verbose)
    if args.verbose:
        print("\n" + "=" * 80)
        print("DETAILED CHUNK INFORMATION (first 3 chunks)")
        print("=" * 80)

        for i, chunk in enumerate(chunks[:3]):
            print(f"\n--- Chunk {i} ---")
            print(f"Section: {' > '.join(chunk.section_path)}")
            print(f"Tokens: {chunk.token_count}")
            print(f"Offset: {chunk.start_offset}-{chunk.end_offset}")
            print(f"Content types: {[ct.value for ct in chunk.content_types]}")
            print(f"Metadata: {chunk.metadata}")
            print(f"\nText preview (first 200 chars):")
            preview = chunk.text[:200].replace("\n", "\n  ")
            print(f"  {preview}")
            if len(chunk.text) > 200:
                print("  ...")

    # Code block preservation check
    code_chunks = [c for c in chunks if c.metadata.get("has_code")]
    if code_chunks:
        print("\n" + "=" * 80)
        print(f"CODE BLOCK PRESERVATION CHECK")
        print("=" * 80)
        print(f"\n✅ Chunks containing code blocks: {len(code_chunks)}")

        for i, chunk in enumerate(code_chunks[:2]):
            code_delimiters = chunk.text.count("```")
            is_closed = code_delimiters % 2 == 0
            status = "✅ Properly closed" if is_closed else "❌ BROKEN!"
            print(
                f"  Chunk {i}: {code_delimiters} delimiters (```) - {status}"
            )

    print("\n" + "=" * 80)
    print("✅ CHUNKING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
