"""Tests for the Writer agent."""

from unittest.mock import patch

from argus.agents.writer import create_writer_agent
from argus.tools.writing import format_as_markdown, write_draft


class TestWriterAgent:
    """Tests for Writer agent creation and configuration."""

    @patch("argus.agents.writer.SqliteDb")
    @patch("argus.agents.writer.create_writer_model")
    def test_create_writer_agent(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Writer agent has correct name, role, and tools."""
        agent = create_writer_agent()

        assert agent.name == "Writer"
        assert "Content writer" in agent.role
        assert agent.markdown is True
        assert agent.add_history_to_context is True

    @patch("argus.agents.writer.SqliteDb")
    @patch("argus.agents.writer.create_writer_model")
    def test_writer_has_correct_tools(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Writer agent has all required writing tools."""
        agent = create_writer_agent()

        tool_names = [t.__name__ for t in agent.tools]
        assert "write_draft" in tool_names
        assert "format_as_markdown" in tool_names

    @patch("argus.agents.writer.SqliteDb")
    @patch("argus.agents.writer.create_writer_model")
    def test_writer_has_instructions(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Writer agent has non-empty instructions."""
        agent = create_writer_agent()

        assert agent.instructions is not None
        assert len(agent.instructions) > 0


class TestWritingTools:
    """Tests for writing tool functions."""

    def test_write_draft_creates_file(self, tmp_path, monkeypatch):
        """write_draft creates a file with title and content."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "drafts").mkdir(parents=True)

        result = write_draft(
            title="Test Title",
            content="Test content here",
            output_path="test.md",
        )

        assert "Draft written" in result
        written_file = tmp_path / "data" / "drafts" / "test.md"
        assert written_file.exists()

        content = written_file.read_text(encoding="utf-8")
        assert "# Test Title" in content
        assert "Test content here" in content

    def test_format_as_markdown(self):
        """format_as_markdown wraps content in markdown."""
        result = format_as_markdown("Hello world")
        assert "## Formatted Content" in result
        assert "Hello world" in result
