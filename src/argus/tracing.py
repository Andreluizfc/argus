"""Langfuse tracing for Argus.

Uses Langfuse's REST ingestion API to create traces and
generation observations with token usage metrics.
"""

import datetime
import logging
import os
import uuid

import requests

from argus.config import settings

logger = logging.getLogger(__name__)

_base_url: str = ""
_auth: tuple[str, str] = ("", "")
_enabled: bool = False


def init_tracing() -> None:
    """Initialize Langfuse REST API connection."""
    global _base_url, _auth, _enabled

    if not settings.langfuse_enabled:
        return

    _base_url = os.environ.get(
        "LANGFUSE_BASE_URL",
        "http://localhost:4000",
    )
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        logger.warning("Langfuse keys not set — tracing disabled")
        return

    _auth = (public_key, secret_key)

    try:
        resp = requests.get(
            f"{_base_url}/api/public/traces?limit=1",
            auth=_auth,
            timeout=5,
        )
        if resp.status_code == 200:
            _enabled = True
            logger.info("Langfuse connection verified")
        else:
            logger.warning(
                f"Langfuse auth failed: {resp.status_code}"
            )
    except requests.ConnectionError:
        logger.warning("Langfuse not reachable — tracing disabled")


def get_langfuse_enabled() -> bool:
    """Check if Langfuse tracing is active."""
    return _enabled


def trace_request(
    name: str,
    input_text: str,
    output_text: str,
    duration_ms: float,
    token_metrics: dict | None = None,
    metadata: dict | None = None,
) -> str | None:
    """Create a Langfuse trace + generation with token usage.

    Args:
        name: Trace name (e.g. "teams/content-team").
        input_text: User message or request description.
        output_text: Agent response or status.
        duration_ms: Total request duration in ms.
        token_metrics: Token usage dict from Agno response
            metrics (input_tokens, output_tokens, etc).
        metadata: Additional metadata dict.
    """
    if not _enabled:
        return None

    trace_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    now = datetime.datetime.now(
        tz=datetime.UTC,
    ).isoformat()

    metrics = token_metrics or {}
    model_details = {}
    if metrics.get("details", {}).get("model"):
        model_details = metrics["details"]["model"][0]

    model_name = model_details.get("id", "unknown")
    input_tokens = metrics.get("input_tokens", 0)
    output_tokens = metrics.get("output_tokens", 0)
    total_tokens = metrics.get("total_tokens", 0)
    ttft = metrics.get("time_to_first_token")

    # Provider-level metrics (Ollama internals)
    provider_metrics = model_details.get("provider_metrics", {})

    batch = [
        # 1. Create trace
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now,
            "body": {
                "id": trace_id,
                "name": name,
                "input": input_text,
                "output": output_text,
                "metadata": {
                    **(metadata or {}),
                    "duration_ms": round(duration_ms, 2),
                },
            },
        },
        # 2. Create generation with token usage
        {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": now,
            "body": {
                "id": generation_id,
                "traceId": trace_id,
                "name": f"{name}/generation",
                "model": model_name,
                "modelParameters": {
                    "provider": model_details.get(
                        "provider", "Ollama"
                    ),
                },
                "input": input_text,
                "output": output_text,
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                "metadata": {
                    "time_to_first_token_s": ttft,
                    "duration_ms": round(duration_ms, 2),
                    "ollama_total_duration_ns": (
                        provider_metrics.get("total_duration")
                    ),
                    "ollama_load_duration_ns": (
                        provider_metrics.get("load_duration")
                    ),
                    "ollama_prompt_eval_ns": (
                        provider_metrics.get("prompt_eval_duration")
                    ),
                    "ollama_eval_ns": (
                        provider_metrics.get("eval_duration")
                    ),
                },
            },
        },
    ]

    try:
        requests.post(
            f"{_base_url}/api/public/ingestion",
            json={"batch": batch},
            auth=_auth,
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"Langfuse trace failed: {e}")

    return trace_id
