from pydantic import BaseSettings, Field


class OpenTelemetrySettings(BaseSettings):
    # We use variables for opentelemetry without prefix OPENTELEMETRY__ to avoid conflicts with opentelemetry.sdk
    otel_exporter_otlp_traces_endpoint: str | None = Field(None, env="OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
