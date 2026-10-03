"""OpenAI-compatible LLM client for structured tool calling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.config import Settings, get_settings
from app.observability.metrics import observe_llm_request
from app.observability.tracing import get_tracer
from app.security.redaction import redact_object


class LLMError(Exception):
    """Base LLM client error."""


class LLMConfigError(LLMError):
    """Missing or invalid LLM configuration."""


class LLMRequestError(LLMError):
    """Transport or API failure talking to the LLM provider."""


@dataclass(slots=True)
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMMessage:
    role: str
    content: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(slots=True)
class LLMResponse:
    message: LLMMessage
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClientProtocol(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...

    async def aclose(self) -> None: ...


class LLMClient:
    """Minimal OpenAI Chat Completions client (httpx, no SDK)."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._settings = settings or get_settings()
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._settings.openai_timeout_seconds),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> LLMClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        api_key = self._settings.openai_api_key
        if api_key is None or not api_key.get_secret_value():
            raise LLMConfigError("OPENAI_API_KEY is not configured")

        # Redact secrets/PII from untrusted monitoring content before LLM submission.
        safe_messages = redact_object(
            messages,
            redact_emails=self._settings.redact_emails,
        )
        if not isinstance(safe_messages, list):
            raise LLMRequestError("Failed to prepare redacted LLM messages")

        payload: dict[str, Any] = {
            "model": self._settings.openai_model,
            "messages": safe_messages,
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        tracer = get_tracer("app.clients.llm")
        with tracer.start_as_current_span("llm.complete") as span:
            span.set_attribute("llm.model", self._settings.openai_model)
            try:
                response = await self._client.post(
                    "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key.get_secret_value()}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                observe_llm_request(status="error")
                raise LLMRequestError("LLM request timed out") from exc
            except httpx.HTTPError as exc:
                observe_llm_request(status="error")
                raise LLMRequestError(f"LLM transport error: {exc}") from exc

            if response.status_code >= 400:
                observe_llm_request(status="error")
                raise LLMRequestError(
                    f"LLM API error {response.status_code}: {response.text[:500]}"
                )

            data = response.json()
            if not isinstance(data, dict):
                observe_llm_request(status="error")
                raise LLMRequestError("LLM response was not a JSON object")
            observe_llm_request(status="success")
            return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMRequestError("LLM response missing choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise LLMRequestError("LLM choice was not an object")
        message = first.get("message")
        if not isinstance(message, dict):
            raise LLMRequestError("LLM message missing")

        tool_calls: list[LLMToolCall] = []
        raw_calls = message.get("tool_calls") or []
        if isinstance(raw_calls, list):
            for call in raw_calls:
                if not isinstance(call, dict):
                    continue
                function = call.get("function")
                if not isinstance(function, dict):
                    continue
                arguments = _parse_arguments(function.get("arguments"))
                tool_calls.append(
                    LLMToolCall(
                        id=str(call.get("id") or ""),
                        name=str(function.get("name") or ""),
                        arguments=arguments,
                    )
                )

        content = message.get("content")
        return LLMResponse(
            message=LLMMessage(
                role=str(message.get("role") or "assistant"),
                content=str(content) if content is not None else None,
                tool_calls=tool_calls,
            ),
            raw=data,
        )


class ScriptedLLMClient:
    """Test double that returns a scripted sequence of LLM responses."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0

    async def aclose(self) -> None:
        return None

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        _ = (messages, tools)
        if self._index >= len(self._responses):
            return LLMResponse(
                message=LLMMessage(
                    role="assistant",
                    content="Investigation complete with available evidence.",
                )
            )
        response = self._responses[self._index]
        self._index += 1
        return response


def _parse_arguments(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        import json

        if not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {}
