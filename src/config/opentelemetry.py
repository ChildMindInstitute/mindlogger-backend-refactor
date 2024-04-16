from pydantic import BaseSettings


class OpenTelemetrySettings(BaseSettings):
    otel_exporter_otlp_traces_endpoint: str = ""
