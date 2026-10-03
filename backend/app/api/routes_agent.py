"""Agent chat routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.api.deps import (
    get_db,
    get_llm_client,
    get_loki_client,
    get_prometheus_client,
)
from app.clients.llm import LLMClientProtocol
from app.clients.loki import LokiClient
from app.clients.prometheus import PrometheusClient
from app.config import Settings, get_settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["agent"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Prometheus = Annotated[PrometheusClient, Depends(get_prometheus_client)]
Loki = Annotated[LokiClient, Depends(get_loki_client)]
LLM = Annotated[LLMClientProtocol, Depends(get_llm_client)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    http_request: Request,
    session: DbSession,
    prometheus: Prometheus,
    loki: Loki,
    llm: LLM,
    settings: AppSettings,
) -> AgentChatResponse:
    """Investigate a dashboard question with read-only tools and grounded evidence."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message must not be empty",
        )

    orchestrator = AgentOrchestrator(
        llm=llm,
        prometheus=prometheus,
        loki=loki,
        session=session,
        settings=settings,
    )
    return await orchestrator.run(
        request,
        request_id=str(getattr(http_request.state, "request_id", "unknown")),
        user_identity=str(getattr(http_request.state, "user_identity", "anonymous")),
    )
