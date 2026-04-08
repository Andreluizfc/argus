"""Argus system configuration.

Centralized settings for Ollama connection, model selection,
and application behavior.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = {"env_prefix": "ARGUS_"}

    # Ollama connection
    ollama_host: str = "http://localhost:11434"

    # Model assignments
    leader_model: str = "qwen3:1.7b"
    researcher_model: str = "qwen3:0.6b"
    writer_model: str = "qwen3:0.6b"

    # Persistence
    database_path: Path = Path("data/agno.db")

    # Agent behavior
    max_history_runs: int = 5
    stream_responses: bool = True

    # Langfuse observability
    langfuse_enabled: bool = True


settings = Settings()
