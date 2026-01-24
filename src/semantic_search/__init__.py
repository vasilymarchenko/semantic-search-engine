"""
Semantic Search Engine - Content-Aware Chunking

A Python library for intelligent document chunking with support for
markdown, code, and other content types.
"""

__version__ = "0.1.0"
__author__ = "Vasyl"

from semantic_search.models import (
    ContentType,
    ContentBlock,
    Chunk,
)
from semantic_search.chunking.base import ChunkingStrategy
from semantic_search.chunking.markdown import MarkdownChunker

__all__ = [
    "ContentType",
    "ContentBlock",
    "Chunk",
    "ChunkingStrategy",
    "MarkdownChunker",
]
