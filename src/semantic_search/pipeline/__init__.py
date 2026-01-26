"""Pipeline-level application services.

These modules are designed to be reusable from both:
- CLI entrypoints
- Azure Function (HTTP trigger) handlers

Avoid UI concerns (printing/progress bars) here.
"""

from .ingestion import IngestionOptions, IngestionResult, IngestionService

__all__ = ["IngestionOptions", "IngestionResult", "IngestionService"]
