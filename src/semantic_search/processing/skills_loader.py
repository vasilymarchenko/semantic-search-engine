"""
Skills loader — reads skill prompt files from local filesystem (dev) or Azure Blob (prod).

Backend is controlled by the SKILLS_BACKEND environment variable:
  "local"  — reads from SKILLS_LOCAL_PATH directory (default for development)
  "blob"   — reads from Azure Blob Storage container (production)

Results are cached in-process to avoid repeated I/O across warm invocations.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillsLoader:
    def __init__(
        self,
        backend: str,
        local_path: str,
        blob_connection: str,
        blob_container: str,
    ) -> None:
        self._backend = backend
        self._local_root = Path(local_path)
        self._blob_connection = blob_connection
        self._blob_container = blob_container
        self._cache: dict[str, str] = {}

    async def load(self, path: str, fallback: str | None = None) -> str:
        """
        Load a skill file by relative path, with optional fallback.

        Caches the result for subsequent calls within the same process lifetime.
        """
        if path in self._cache:
            return self._cache[path]

        try:
            content = await self._read(path)
            self._cache[path] = content
            return content
        except FileNotFoundError:
            if fallback:
                logger.warning("Skill %r not found, using fallback %r", path, fallback)
                return await self.load(fallback)
            raise

    async def _read(self, path: str) -> str:
        match self._backend:
            case "local":
                return self._read_local(path)
            case "blob":
                return await self._read_blob(path)
            case _:
                raise ValueError(f"Unknown skills backend: {self._backend!r}")

    def _read_local(self, path: str) -> str:
        full = self._local_root / path
        if not full.exists():
            raise FileNotFoundError(f"Skill file not found: {full}")
        return full.read_text(encoding="utf-8")

    async def _read_blob(self, path: str) -> str:
        from azure.storage.blob import BlobServiceClient  # type: ignore[import-untyped]

        def _sync() -> str:
            client = BlobServiceClient.from_connection_string(self._blob_connection)
            blob = (
                client.get_container_client(self._blob_container).get_blob_client(path)
            )
            return blob.download_blob().readall().decode("utf-8")

        return await asyncio.to_thread(_sync)
