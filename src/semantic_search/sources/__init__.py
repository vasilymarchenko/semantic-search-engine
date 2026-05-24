"""Source detection and content acquisition layer (ADR-006, Layer 1)."""

from semantic_search.sources.detector import SourceType, detect_source_type
from semantic_search.sources.extractors import ContentExtractor, get_extractor

__all__ = ["SourceType", "detect_source_type", "ContentExtractor", "get_extractor"]
