"""Ollama model definitions for Argus agents."""

from agno.models.ollama import Ollama

from argus.config import settings


def create_leader_model() -> Ollama:
    """Create the team leader model (Qwen3 1.7B)."""
    return Ollama(
        id=settings.leader_model,
        host=settings.ollama_host,
    )


def create_researcher_model() -> Ollama:
    """Create the researcher agent model (Qwen3 0.6B)."""
    return Ollama(
        id=settings.researcher_model,
        host=settings.ollama_host,
    )


def create_writer_model() -> Ollama:
    """Create the writer agent model (Qwen3 0.6B)."""
    return Ollama(
        id=settings.writer_model,
        host=settings.ollama_host,
    )
