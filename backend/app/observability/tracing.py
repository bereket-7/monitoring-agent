"""Optional OpenTelemetry tracing setup."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)
_provider: TracerProvider | None = None


def setup_tracing(settings: Settings) -> None:
    """Configure OTLP exporter when enabled; otherwise keep default no-op tracer."""
    global _provider
    if not settings.otel_enabled:
        return
    if _provider is not None:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name or settings.app_name,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.otel_exporter_otlp_endpoint:
        exporter: OTLPSpanExporter | ConsoleSpanExporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
    else:
        exporter = ConsoleSpanExporter()
        logger.info("otel_console_exporter_enabled")

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider
    logger.info("otel_tracing_enabled", endpoint=settings.otel_exporter_otlp_endpoint or "console")


def shutdown_tracing() -> None:
    global _provider
    if _provider is not None:
        _provider.shutdown()
        _provider = None


def get_tracer(name: str = "monitoring-dashboard-agent") -> trace.Tracer:
    return trace.get_tracer(name)
