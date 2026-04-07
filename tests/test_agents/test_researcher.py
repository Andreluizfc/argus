"""Tests for the Researcher agent."""

from unittest.mock import patch

from argus.agents.researcher import create_researcher_agent
from argus.tools.research import (
    extract_key_facts,
    search_documents,
    summarize_findings,
)


class TestResearcherAgent:
    """Tests for Researcher agent creation and configuration."""

    @patch("argus.agents.researcher.SqliteDb")
    @patch("argus.agents.researcher.create_researcher_model")
    def test_create_researcher_agent(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Researcher agent has correct name, role, and tools."""
        agent = create_researcher_agent()

        assert agent.name == "Researcher"
        assert "Research specialist" in agent.role
        assert agent.markdown is True
        assert agent.add_history_to_context is True

    @patch("argus.agents.researcher.SqliteDb")
    @patch("argus.agents.researcher.create_researcher_model")
    def test_researcher_has_correct_tools(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Researcher agent has all required research tools."""
        agent = create_researcher_agent()

        tool_names = [t.__name__ for t in agent.tools]
        assert "search_documents" in tool_names
        assert "extract_key_facts" in tool_names
        assert "summarize_findings" in tool_names

    @patch("argus.agents.researcher.SqliteDb")
    @patch("argus.agents.researcher.create_researcher_model")
    def test_researcher_has_instructions(
        self,
        mock_model_fn,
        mock_db_cls,
    ):
        """Researcher agent has non-empty instructions."""
        agent = create_researcher_agent()

        assert agent.instructions is not None
        assert len(agent.instructions) > 0


class TestResearchTools:
    """Tests for research tool functions."""

    def test_search_documents(self):
        """search_documents returns results for a query."""
        result = search_documents("python async")
        assert "python async" in result
        assert "Found" in result

    def test_extract_key_facts(self):
        """extract_key_facts processes text input."""
        result = extract_key_facts("Some important text here")
        assert "Key facts" in result
        assert "25 chars" in result

    def test_summarize_findings(self):
        """summarize_findings creates a summary."""
        result = summarize_findings(
            topic="testing",
            findings="Various findings about testing...",
        )
        assert "testing" in result
        assert "Summary" in result

    def test_summarize_findings_truncates_long_input(self):
        """summarize_findings truncates findings over 200 chars."""
        long_text = "x" * 500
        result = summarize_findings(
            topic="test",
            findings=long_text,
        )
        assert "..." in result
