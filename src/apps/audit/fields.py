from asgi_correlation_id.context import correlation_id
from ddtrace.trace import tracer
from fastapi import Request

from apps.shared.exception import BaseError

from .enums import EventOutcome


def http_request_fields(request: Request) -> dict:
    """Audit fields derived from HTTP request."""
    return {
        "client_ip": request.client and request.client.host,
        "http_request_id": correlation_id.get(),
        "http_request_method": request.method,
        "url_path": request.url.path,
        "user_agent": request.headers.get("user-agent"),
        "trace_id": (span := tracer.current_span()) and str(span.trace_id),
    }


def http_error_fields(error: BaseError) -> dict:
    """Audit fields derived from HTTP error."""
    return {
        "event_outcome": EventOutcome.FAILURE,
        "error_type": type(error).__name__,
        "http_response_status_code": error.status_code,
    }
