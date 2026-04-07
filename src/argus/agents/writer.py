"""Writer agent definition."""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from argus.config import settings
from argus.models import create_writer_model
from argus.tools.writing import (
    format_as_markdown,
    write_draft,
)


def create_writer_agent() -> Agent:
    """Create the Writer sub-agent."""
    return Agent(
        name="Writer",
        role="Content writer that creates polished documents",
        model=create_writer_model(),
        tools=[
            write_draft,
            format_as_markdown,
        ],
        instructions=[
            "You are a skilled content writer.",
            "Use research provided by team members as source material.",
            "Write clear, well-structured content.",
            "Always format output as Markdown.",
            "Use write_draft to save final documents.",
        ],
        db=SqliteDb(
            session_table="writer_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        num_history_runs=settings.max_history_runs,
        markdown=True,
    )
