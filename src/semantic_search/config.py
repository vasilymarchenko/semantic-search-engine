"""
Application configuration via pydantic-settings.

All environment variable access goes through this module — never os.getenv() elsewhere.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_key: SecretStr = SecretStr("")
    cosmos_database: str = "semantic-search"
    cosmos_container: str = "items"

    # OpenAI embeddings
    openai_api_key: SecretStr = SecretStr("")
    openai_embedding_model: str = "text-embedding-3-small"

    # Anthropic / Claude (model tiers per ADR-008)
    anthropic_api_key: SecretStr = SecretStr("")
    router_model: str = "claude-haiku-4-5-20251001"   # source classification
    processor_model: str = "claude-sonnet-4-6"         # summary + key concepts

    # Skills loader
    skills_backend: str = "local"               # "local" | "blob"
    skills_local_path: str = "skills"
    skills_blob_connection: str = ""
    skills_blob_container: str = "skills"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
