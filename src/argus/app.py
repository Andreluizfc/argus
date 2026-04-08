"""Argus application entrypoint.

Exposes the Content Team via AgentOS FastAPI runtime
with Langfuse observability via request middleware.
"""

import json
import time

from agno.os import AgentOS
from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import StreamingResponse

from argus.agents.researcher import create_researcher_agent
from argus.agents.writer import create_writer_agent
from argus.feedback import router as feedback_router
from argus.teams.content import create_content_team
from argus.tracing import init_tracing, trace_request

# Initialize Langfuse
init_tracing()

agent_os = AgentOS(
    agents=[
        create_researcher_agent(),
        create_writer_agent(),
    ],
    teams=[create_content_team()],
    tracing=False,
)

app = agent_os.get_app()
app.include_router(feedback_router)


class LangfuseMiddleware(BaseHTTPMiddleware):
    """Traces team/agent run requests to Langfuse with token metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        if "/runs" not in path:
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # Extract component name from path
        parts = path.strip("/").split("/")
        component = parts[1] if len(parts) >= 3 else "unknown"
        component_type = parts[0] if parts else "unknown"

        # Read response body to extract token metrics
        # Only for non-streaming JSON responses
        token_metrics = None
        input_text = f"[request to {path}]"
        output_text = f"[status {response.status_code}]"

        if (
            response.status_code == 200
            and not isinstance(response, StreamingResponse)
        ):
            body = b""
            async for chunk in response.body_iterator:
                body += (
                    chunk
                    if isinstance(chunk, bytes)
                    else chunk.encode()
                )

            try:
                data = json.loads(body)
                token_metrics = data.get("metrics")
                output_text = (data.get("content") or "")[:500]
            except (json.JSONDecodeError, AttributeError):
                pass

            # Rebuild response with the consumed body
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        trace_request(
            name=f"{component_type}/{component}",
            input_text=input_text,
            output_text=output_text,
            duration_ms=duration_ms,
            token_metrics=token_metrics,
            metadata={
                "path": path,
                "status_code": response.status_code,
                "component_type": component_type,
                "component": component,
            },
        )

        return response


app.add_middleware(LangfuseMiddleware)
