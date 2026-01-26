"""Typer-based CLI for the ingestion pipeline.

This CLI provides the dev-time ingestion flow:
1) Load content (URL or file)
2) Process to normalized markdown
3) Chunk the markdown
4) (Optional) save results to an output directory

It is designed as the long-term CLI surface (future: embed/store/search/stats).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from semantic_search.pipeline import IngestionOptions, IngestionService
from semantic_search.utils.fetcher import detect_source_type

app = typer.Typer(
    help="Semantic Search ingestion pipeline: load, process, chunk, save.",
    add_completion=False,
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _print_header(text: str) -> None:
    console.print("\n" + "=" * 80)
    console.print(text)
    console.print("=" * 80)


def _print_section(text: str) -> None:
    console.print("\n" + "-" * 80)
    console.print(text)
    console.print("-" * 80)


def _print_verbose_info(chunks: list) -> None:
    _print_section("🔍 DETAILED CHUNK INFORMATION")

    for i, chunk in enumerate(chunks[:3], start=1):
        console.print(f"\n--- Chunk {i} ---")
        console.print(f"Section: {' > '.join(chunk.section_path)}")
        console.print(f"Tokens: {chunk.token_count}")
        console.print(f"Offset: {chunk.start_offset}-{chunk.end_offset}")
        console.print(f"Content types: {[ct.value for ct in chunk.content_types]}")
        if chunk.metadata:
            console.print(f"Metadata: {chunk.metadata}")

        preview = chunk.text[:200].replace("\n", "\n  ")
        console.print("\nText preview (first 200 chars):")
        console.print(f"  {preview}")
        if len(chunk.text) > 200:
            console.print("  ...")

    if len(chunks) > 3:
        console.print(f"\n... and {len(chunks) - 3} more chunks")

    code_chunks = [c for c in chunks if c.metadata.get("has_code")]
    if code_chunks:
        console.print("\n" + "-" * 80)
        console.print("CODE BLOCK PRESERVATION CHECK")
        console.print("-" * 80)
        console.print(f"✅ Chunks with code blocks: {len(code_chunks)}")

        for i, chunk in enumerate(code_chunks[:3], start=1):
            delimiters = chunk.text.count("```")
            is_closed = delimiters % 2 == 0
            status = "✅ Properly closed" if is_closed else "❌ BROKEN!"
            console.print(f"  Chunk {i}: {delimiters} delimiters (```) - {status}")


def _print_summary(markdown: str, chunks: list, statistics: dict) -> None:
    _print_section("📊 SUMMARY")

    if statistics:
        console.print(
            f"Document: {statistics.get('word_count', 0)} words, {statistics.get('character_count', 0)} characters"
        )
        if "reading_time_minutes" in statistics:
            console.print(f"Reading time: {statistics['reading_time_minutes']} min")

    total_tokens = sum(c.token_count for c in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    min_tokens = min(c.token_count for c in chunks) if chunks else 0
    max_tokens = max(c.token_count for c in chunks) if chunks else 0

    console.print(f"\nChunks: {len(chunks)} total")
    console.print(f"  Total tokens: {total_tokens}")
    console.print(f"  Avg tokens: {avg_tokens:.0f}")
    console.print(f"  Min tokens: {min_tokens}")
    console.print(f"  Max tokens: {max_tokens}")

    ranges = [
        (0, 200, "Very small"),
        (200, 400, "Optimal"),
        (400, 600, "Large"),
        (600, 1000, "Very large"),
    ]

    console.print("\n📈 Token distribution:")
    for min_t, max_t, label in ranges:
        count = sum(1 for c in chunks if min_t <= c.token_count < max_t)
        if count > 0:
            percentage = (count / len(chunks)) * 100
            console.print(f"  {label:12s}: {count:2d} chunks ({percentage:5.1f}%)")


async def _run_ingestion(
    source: str,
    output_dir: Path,
    max_tokens: int,
    overlap_tokens: int,
    min_tokens: int,
    verbose: bool,
    save: bool,
) -> None:
    _print_header("🚀 INGESTION PIPELINE")

    source_type = detect_source_type(source)
    console.print(f"📍 Source type: {source_type}")

    options = IngestionOptions(
        output_dir=output_dir,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        min_tokens=min_tokens,
        save_outputs=save,
        overwrite_output_dir=True,
    )

    service = IngestionService()

    _print_section("📥 STEP 1: LOAD CONTENT")
    _print_section("🔄 STEP 2: PROCESS TO MARKDOWN")
    _print_section("✂️  STEP 3: CHUNK MARKDOWN")
    _print_section("💾 STEP 4: SAVE OUTPUT")

    try:
        result = await service.ingest(source, options)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"File not found: {exc}") from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    markdown = result.document.content
    chunks = result.chunks
    statistics = result.document.statistics

    if result.output_dir and result.output_basename:
        console.print(f"💾 Saved document: {result.output_dir / (result.output_basename + '.md')}")
        console.print(
            f"💾 Saved {len(chunks)} chunks: chunk_1.md to chunk_{len(chunks)}.md"
        )
        if "metadata" in result.saved_files:
            console.print(f"💾 Saved metadata: {result.saved_files['metadata']}")

    _print_summary(markdown, chunks, statistics)

    if verbose:
        _print_verbose_info(chunks)

    _print_header("✅ INGESTION COMPLETE")
    if save:
        console.print(f"\n📂 Output directory: {output_dir.absolute()}")
    console.print("\n🔄 Next steps:")
    console.print("  1. Review the normalized markdown document")
    console.print("  2. Check the chunks for quality")
    console.print("  3. Next phase: Generate embeddings and index to vector store")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(
        None,
        help="URL or file path (supported: .html, .htm, .md, .markdown)",
        show_default=False,
    ),
    save: bool = typer.Option(
        True,
        "--save",
        help="Save normalized markdown, chunks, and metadata to the output directory.",
    ),
    output_dir: Path = typer.Option(
        Path("ingestion_output"),
        "--output-dir",
        "-o",
        help="Output directory (default: ingestion_output/)",
    ),
    max_tokens: int = typer.Option(
        400,
        "--max-tokens",
        help="Maximum tokens per chunk (default: 400)",
    ),
    overlap_tokens: int = typer.Option(
        50,
        "--overlap-tokens",
        help="Token overlap between chunks (default: 50)",
    ),
    min_tokens: int = typer.Option(
        100,
        "--min-tokens",
        help="Minimum tokens per chunk (default: 100)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed chunk information and diagnostics",
    ),
) -> None:
    """Run ingestion (default command).

    Examples:
      ingestion-cli https://example.com/article
      ingestion-cli document.html
      ingestion-cli document.md
      ingestion-cli https://fastapi.tiangolo.com/ --max-tokens 600
    """

    if ctx.invoked_subcommand is not None:
        return

    if not source:
        console.print("Error: SOURCE is required. Use --help for usage.", style="red")
        raise typer.Exit(code=2)

    try:
        asyncio.run(
            _run_ingestion(
                source=source,
                output_dir=output_dir,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                min_tokens=min_tokens,
                verbose=verbose,
                save=save,
            )
        )
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"\n❌ Unexpected error: {exc}", style="red")
        raise typer.Exit(code=1)


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()
