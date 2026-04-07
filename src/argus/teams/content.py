"""Content creation team definition."""

from agno.db.sqlite import SqliteDb
from agno.team import Team
from agno.team.team import TeamMode

from argus.agents.researcher import create_researcher_agent
from argus.agents.writer import create_writer_agent
from argus.config import settings
from argus.models import create_leader_model


def create_content_team() -> Team:
    """Create the content creation team.

    Team leader (Qwen3 1.7B) coordinates:
    - Researcher (Qwen3 0.6B): finds and analyzes information
    - Writer (Qwen3 0.6B): creates polished content
    """
    return Team(
        name="Content Team",
        mode=TeamMode.coordinate,
        model=create_leader_model(),
        members=[
            create_researcher_agent(),
            create_writer_agent(),
        ],
        instructions=[
            "You are the team leader for content creation.",
            "Break tasks into research and writing phases.",
            "First delegate research to the Researcher agent.",
            "Then pass research results to the Writer agent.",
            "Review the final output before delivering.",
        ],
        db=SqliteDb(
            session_table="team_sessions",
            db_file=str(settings.database_path),
        ),
        add_history_to_context=True,
        markdown=True,
    )
