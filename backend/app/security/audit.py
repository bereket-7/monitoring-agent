"""Structured audit events with secret redaction."""

from __future__ import annotations

from typing import Any

from app.logging import get_logger
from app.security.redaction import redact_object

logger = get_logger(__name__)


def emit_audit_event(
    event: str,
    *,
    request_id: str | None = None,
    user_identity: str | None = None,
    dashboard_uid: str | None = None,
    analysis_id: str | None = None,
    tool_name: str | None = None,
    tool_arguments: dict[str, Any] | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    **extra: Any,
) -> None:
    """Emit a structured audit log line; never include raw secrets."""
    payload: dict[str, Any] = {
        "audit_event": event,
        "request_id": request_id,
        "user_identity": user_identity,
        "dashboard_uid": dashboard_uid,
        "analysis_id": analysis_id,
        "tool_name": tool_name,
        "status": status,
        "duration_ms": duration_ms,
    }
    if tool_arguments is not None:
        payload["tool_arguments"] = redact_object(tool_arguments)
    for key, value in extra.items():
        payload[key] = redact_object(value)
    logger.info("audit", **{k: v for k, v in payload.items() if v is not None})
