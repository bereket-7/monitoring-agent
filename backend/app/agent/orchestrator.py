"""Bounded agent orchestration loop with structured tool calling."""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.evidence import record_tool_result
from app.agent.formatter import format_response
from app.agent.prompts import build_system_messages
from app.agent.state import AgentState
from app.agent.tools import ToolContext, ToolRegistry, tool_result_message
from app.clients.grafana import GrafanaClient
from app.clients.llm import LLMClientProtocol, LLMConfigError, LLMError, LLMMessage, LLMResponse
from app.clients.loki import LokiClient
from app.clients.prometheus import PrometheusClient
from app.config import Settings, get_settings
from app.logging import get_logger
from app.observability.metrics import observe_agent_request, observe_tool_call
from app.observability.tracing import get_tracer
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.security.audit import emit_audit_event

logger = get_logger(__name__)


class AgentOrchestrator:
    """Run a budgeted investigate → tool → evidence → answer loop."""

    def __init__(
        self,
        *,
        llm: LLMClientProtocol,
        prometheus: PrometheusClient,
        loki: LokiClient,
        session: AsyncSession,
        grafana: GrafanaClient | None = None,
        settings: Settings | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self._llm = llm
        self._prometheus = prometheus
        self._loki = loki
        self._grafana = grafana
        self._session = session
        self._settings = settings or get_settings()
        self._registry = registry or ToolRegistry()

    async def run(
        self,
        request: AgentChatRequest,
        *,
        request_id: str | None = None,
        user_identity: str | None = None,
    ) -> AgentChatResponse:
        started = time.monotonic()
        state = self._initial_state(request)
        tool_context = ToolContext(
            session=self._session,
            prometheus=self._prometheus,
            loki=self._loki,
            grafana=self._grafana,
            settings=self._settings,
        )
        tracer = get_tracer("app.agent.orchestrator")

        try:
            with tracer.start_as_current_span("agent.run") as span:
                span.set_attribute("agent.dashboard_uid", request.dashboard_uid or "")
                while state.final_answer is None:
                    if time.monotonic() - started > self._settings.agent_max_analysis_seconds:
                        state.stopped_reason = "timeout"
                        state.limitations.append("Analysis time budget exceeded.")
                        break
                    if state.remaining_budget <= 0:
                        state.stopped_reason = "budget_exhausted"
                        state.limitations.append("Tool-call budget exhausted.")
                        break

                    try:
                        llm_response = await self._llm.complete(
                            state.messages,
                            self._registry.list_openai_tools(),
                        )
                    except LLMConfigError as exc:
                        state.stopped_reason = "llm_not_configured"
                        state.limitations.append(str(exc))
                        state.final_answer = (
                            "The LLM provider is not configured. "
                            "Set OPENAI_API_KEY to enable agent chat."
                        )
                        break
                    except LLMError as exc:
                        state.stopped_reason = "llm_error"
                        state.limitations.append(str(exc))
                        state.final_answer = (
                            "The language model request failed before "
                            "investigation could continue."
                        )
                        break

                    message = llm_response.message
                    if message.tool_calls:
                        await self._handle_tool_calls(state, tool_context, llm_response)
                        continue

                    content = (message.content or "").strip()
                    if content:
                        state.final_answer = content
                        self._extract_recommendations(state, content)
                        state.stopped_reason = "completed"
                        break

                    state.stopped_reason = "empty_llm_response"
                    state.limitations.append("Model returned an empty response.")
                    break
        finally:
            duration = time.monotonic() - started
            status = state.stopped_reason or "unknown"
            observe_agent_request(
                status=status,
                duration_seconds=duration,
                findings_count=len(state.findings),
            )
            emit_audit_event(
                "agent_run_complete",
                request_id=request_id,
                user_identity=user_identity,
                dashboard_uid=state.dashboard_uid,
                status=status,
                duration_ms=duration * 1000,
                tool_call_count=len(state.tool_calls),
            )
            logger.info(
                "agent_run_complete",
                dashboard_uid=state.dashboard_uid,
                tool_calls=len(state.tool_calls),
                remaining_budget=state.remaining_budget,
                stopped_reason=state.stopped_reason,
            )

        if state.final_answer is None:
            state.final_answer = self._fallback_answer(state)

        return format_response(state)

    def _initial_state(self, request: AgentChatRequest) -> AgentState:
        time_range: dict[str, Any] = {}
        if request.context.time_range is not None:
            time_range = request.context.time_range.model_dump(by_alias=True, exclude_none=True)

        user_content = request.message
        if request.dashboard_uid:
            user_content += f"\n\nDashboard UID: {request.dashboard_uid}"
        if time_range:
            user_content += f"\nTime range: {json.dumps(time_range)}"
        if request.context.filters:
            user_content += f"\nFilters: {json.dumps(request.context.filters)}"

        messages: list[dict[str, Any]] = [
            *build_system_messages(),
            {"role": "user", "content": user_content},
        ]
        return AgentState(
            user_message=request.message,
            dashboard_uid=request.dashboard_uid,
            time_range=time_range,
            filters=dict(request.context.filters),
            remaining_budget=self._settings.agent_max_tool_calls,
            messages=messages,
        )

    async def _handle_tool_calls(
        self,
        state: AgentState,
        tool_context: ToolContext,
        llm_response: LLMResponse,
    ) -> None:
        assistant_payload: dict[str, Any] = {
            "role": "assistant",
            "content": llm_response.message.content,
            "tool_calls": [
                {
                    "id": call.id or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for idx, call in enumerate(llm_response.message.tool_calls)
            ],
        }
        state.messages.append(assistant_payload)

        for call in llm_response.message.tool_calls:
            if not state.consume_budget():
                state.stopped_reason = "budget_exhausted"
                state.limitations.append("Tool-call budget exhausted mid-batch.")
                break

            call_id = call.id or f"call_{len(state.tool_calls)}"
            tool_started = time.monotonic()
            status = "success"
            try:
                result = await self._registry.execute(call.name, call.arguments, tool_context)
                record_tool_result(
                    state,
                    name=call.name,
                    arguments=call.arguments,
                    status="success",
                    result=result,
                )
                state.messages.append(tool_result_message(call_id, call.name, result))
            except PermissionError as exc:
                status = "denied"
                payload = {"error": str(exc), "observed": False}
                record_tool_result(
                    state,
                    name=call.name,
                    arguments=call.arguments,
                    status="denied",
                    error=str(exc),
                )
                state.messages.append(tool_result_message(call_id, call.name, payload))
            except Exception as exc:
                status = "error"
                payload = {"error": str(exc), "observed": False}
                record_tool_result(
                    state,
                    name=call.name,
                    arguments=call.arguments,
                    status="error",
                    error=str(exc),
                )
                state.messages.append(tool_result_message(call_id, call.name, payload))
            finally:
                duration = time.monotonic() - tool_started
                observe_tool_call(
                    tool_name=call.name,
                    status=status,
                    duration_seconds=duration,
                )
                emit_audit_event(
                    "agent_tool_call",
                    dashboard_uid=state.dashboard_uid,
                    tool_name=call.name,
                    tool_arguments=call.arguments,
                    status=status,
                    duration_ms=duration * 1000,
                )

    def _extract_recommendations(self, state: AgentState, answer: str) -> None:
        marker = "Recommendation"
        if marker.lower() not in answer.lower():
            return
        # Keep model-provided recommendation section text as free-form guidance.
        for line in answer.splitlines():
            stripped = line.strip(" -*")
            if stripped.lower().startswith("recommend"):
                state.recommendations.append(stripped)

    def _fallback_answer(self, state: AgentState) -> str:
        if state.evidence:
            return (
                "Investigation stopped before a final narrative was produced. "
                "Observed evidence was collected and is listed below; "
                "do not treat missing details as facts."
            )
        return (
            "I could not gather enough observed evidence to answer confidently. "
            "Sync the dashboard and ensure monitoring backends are reachable."
        )


def scripted_assistant_text(content: str) -> LLMResponse:
    return LLMResponse(message=LLMMessage(role="assistant", content=content))


def scripted_tool_calls(
    calls: list[tuple[str, dict[str, Any]]],
) -> LLMResponse:
    from app.clients.llm import LLMToolCall

    return LLMResponse(
        message=LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                LLMToolCall(id=f"call_{idx}", name=name, arguments=arguments)
                for idx, (name, arguments) in enumerate(calls)
            ],
        )
    )
