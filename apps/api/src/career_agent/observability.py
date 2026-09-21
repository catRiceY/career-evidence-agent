"""Privacy-aware OpenTelemetry setup with optional Langfuse OTLP export."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class OtlpExportSettings:
    endpoint: str
    headers: Mapping[str, str]


def export_settings_from_environment(env: Mapping[str, str] | None = None) -> OtlpExportSettings | None:
    # An explicit empty mapping is a valid test/local configuration: it must
    # not silently inherit process credentials from the surrounding shell.
    env = os.environ if env is None else env
    explicit_endpoint = env.get("CAREER_AGENT_OTEL_EXPORTER_OTLP_ENDPOINT")
    if explicit_endpoint:
        return OtlpExportSettings(endpoint=explicit_endpoint.rstrip("/"), headers={})
    public_key, secret_key = env.get("LANGFUSE_PUBLIC_KEY"), env.get("LANGFUSE_SECRET_KEY")
    host = env.get("LANGFUSE_HOST") or env.get("LANGFUSE_BASE_URL")
    if not (public_key and secret_key and host):
        return None
    basic = b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return OtlpExportSettings(
        endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {basic}", "x-langfuse-ingestion-version": "4"},
    )


_configured = False


def configure_observability() -> bool:
    """Configure export once; prompts, answers and API keys are never traced."""
    global _configured
    settings = export_settings_from_environment()
    if _configured or settings is None:
        return False
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "career-evidence-agent-api"),
        "service.version": "0.1.0",
    }))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.endpoint, headers=settings.headers)))
    trace.set_tracer_provider(provider)
    _configured = True
    return True


def trace_event(name: str, attributes: Mapping[str, str | int | bool]) -> None:
    """Emit operational metadata only; caller must not attach raw user text."""
    try:
        from opentelemetry import trace
    except ImportError:
        # Keep the core product runnable before optional observability extras
        # are installed. `uv sync` turns this into a real span automatically.
        return
    with trace.get_tracer("career_evidence_agent").start_as_current_span(name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
