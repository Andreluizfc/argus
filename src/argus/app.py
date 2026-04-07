"""Argus application entrypoint.

Exposes the Content Team via AgentOS FastAPI runtime.
"""

from agno.os import AgentOS

from argus.agents.researcher import create_researcher_agent
from argus.agents.writer import create_writer_agent
from argus.teams.content import create_content_team

agent_os = AgentOS(
    agents=[
        create_researcher_agent(),
        create_writer_agent(),
    ],
    teams=[create_content_team()],
    tracing=False,
)

app = agent_os.get_app()
