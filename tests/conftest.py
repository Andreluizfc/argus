"""Shared test fixtures for Argus."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_ollama_model():
    """Mock Ollama model that returns predictable responses."""
    with patch("agno.models.ollama.Ollama") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_sqlite_db():
    """Mock SqliteDb to avoid filesystem writes during tests."""
    with patch("agno.db.sqlite.SqliteDb") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance
