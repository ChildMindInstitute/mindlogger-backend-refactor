from asgi_correlation_id.context import correlation_id
from ddtrace.trace import tracer
from fastapi import Request
from fastapi.routing import APIRoute

from apps.shared.exception import BaseError

from .enums import EventOutcome


def http_audit_fields(request: Request, error: BaseError | None = None) -> dict:
    """Audit fields derived from HTTP request/error."""
    route = request.scope.get("route")
    span = tracer.current_span()
    fields = {
        "client_ip": request.client and request.client.host,
        "http_request_id": correlation_id.get(),
        "http_request_method": request.method,
        "http_response_status_code": isinstance(route, APIRoute) and route.status_code or 200,
        "url_path": request.url.path,
        "url_query": request.url.query or None,
        "user_agent": request.headers.get("user-agent"),
        "trace_id": span and str(span.trace_id),
    }
    if error is not None:
        fields["event_outcome"] = EventOutcome.FAILURE
        fields["error_type"] = type(error).__name__
        fields["http_response_status_code"] = error.status_code
    return fields
