"""Configurable secret/PII redaction before LLM prompts and audit logs."""

from __future__ import annotations

import re
from typing import Any

_BEARER_RE = re.compile(r"(?i)\b(bearer\s+)([a-z0-9._\-+=/]{8,})")
_API_KEY_ASSIGN_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b(\s*[:=]\s*)([^\s,;\"']+)"
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_LONG_SECRET_RE = re.compile(r"\b(?:sk|rk|pk)[-_][A-Za-z0-9]{16,}\b")

REDACTED = "[REDACTED]"


def redact_text(value: str, *, redact_emails: bool = True) -> str:
    """Redact common secret patterns from free-form text."""
    redacted = _BEARER_RE.sub(rf"\1{REDACTED}", value)
    redacted = _API_KEY_ASSIGN_RE.sub(rf"\1\2{REDACTED}", redacted)
    redacted = _AWS_KEY_RE.sub(REDACTED, redacted)
    redacted = _LONG_SECRET_RE.sub(REDACTED, redacted)
    if redact_emails:
        redacted = _EMAIL_RE.sub(REDACTED, redacted)
    return redacted


def redact_object(value: Any, *, redact_emails: bool = True) -> Any:
    """Recursively redact strings inside JSON-like structures."""
    if isinstance(value, str):
        return redact_text(value, redact_emails=redact_emails)
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {
                "authorization",
                "api_key",
                "apikey",
                "token",
                "password",
                "secret",
                "grafana_api_token",
                "openai_api_key",
            }:
                result[key] = REDACTED
            else:
                result[key] = redact_object(item, redact_emails=redact_emails)
        return result
    if isinstance(value, list):
        return [redact_object(item, redact_emails=redact_emails) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_object(item, redact_emails=redact_emails) for item in value)
    return value
