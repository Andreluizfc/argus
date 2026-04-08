"""User feedback endpoint for Langfuse scores."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from argus.config import settings

router = APIRouter()


class FeedbackRequest(BaseModel):
    """User feedback on an agent response."""

    trace_id: str
    score: int  # 1 = positive, 0 = negative
    comment: str | None = None


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest) -> dict:
    """Submit user feedback as a Langfuse score."""
    if not settings.langfuse_enabled:
        raise HTTPException(
            status_code=503,
            detail="Langfuse not enabled",
        )

    from argus.tracing import get_langfuse

    client = get_langfuse()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Langfuse not connected",
        )

    client.create_score(
        trace_id=request.trace_id,
        name="user-feedback",
        value=request.score,
        comment=request.comment,
    )

    return {"status": "ok"}
