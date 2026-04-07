"""Researcher agent definition."""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from argus.config import settings
from argus.models import create_researcher_model
from argus.tools.research import (
    extract_key_facts,
    search_documents,
    summarize_findings,
)


def create_researcher_agent() -> Agent:
    """Create the Researcher sub-agent."""
    return Agent(
        name="Researcher",
        role="Research specialist that finds and analyzes information",
        model=create_researcher_model(),
        tools=[
            search_documents,
            extract_key_facts,
            summarize_findings,
        ],
        instructions=[
            "You are a thorough research specialist.",
            "Always use search_documents to find relevant information.",
            "Extract key facts before summarizing.",
            "Provide structured, factual responses.",
            "Never fabricate data — use tools to gather real information.",
        ],
        db=SqliteDb(
            session_table="researcher_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        num_history_runs=settings.max_history_runs,
        markdown=True,
    )
