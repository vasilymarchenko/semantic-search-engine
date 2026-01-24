"""
Abstract base class for chunking strategies.
"""

from abc import ABC, abstractmethod

from semantic_search.models import Chunk


class ChunkingStrategy(ABC):
    """
    Abstract base class for document chunking strategies.

    Different document types (markdown, code, email, PDF) require
    different chunking strategies that respect content boundaries.
    """

    @abstractmethod
    def chunk_document(self, text: str) -> list[Chunk]:
        """
        Split document into searchable chunks.

        Args:
            text: The complete document text

        Returns:
            List of Chunk objects with metadata and offsets
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a text string.

        This is a rough approximation: ~4 characters per token.
        Can be overridden for more accurate counting.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4
