"""Langfuse tracing for Argus.

Uses Langfuse's REST ingestion API directly (not OTel)
because the OTel BatchSpanProcessor has reliability issues
with connection caching during Docker container startup.
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

    # Verify connection
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


def trace_request(
    name: str,
    input_text: str,
    output_text: str,
    duration_ms: float,
    metadata: dict | None = None,
) -> str | None:
    """Create a Langfuse trace via REST ingestion API."""
    if not _enabled:
        return None

    trace_id = str(uuid.uuid4())
    now = datetime.datetime.now(
        tz=datetime.UTC,
    ).isoformat()

    payload = {
        "batch": [
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
        ],
    }

    try:
        requests.post(
            f"{_base_url}/api/public/ingestion",
            json=payload,
            auth=_auth,
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"Langfuse trace failed: {e}")

    return trace_id
