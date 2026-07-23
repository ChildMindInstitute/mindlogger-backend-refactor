from asgi_correlation_id.context import correlation_id
from ddtrace.trace import tracer
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection, Request

from apps.shared.exception import BaseError

from .enums import EventOutcome


def http_audit_fields(conn: HTTPConnection, error: BaseError | StarletteHTTPException | None = None) -> dict:
    """Audit fields derived from an HTTP or WebSocket connection and error."""
    route = conn.scope.get("route")
    span = tracer.current_span()
    fields = {
        "client_ip": conn.client and conn.client.host,
        "http_request_id": correlation_id.get(),
        # WebSocket connections have no HTTP method.
        "http_request_method": conn.method if isinstance(conn, Request) else None,
        "http_response_status_code": isinstance(route, APIRoute) and route.status_code or 200,
        "url_path": conn.url.path,
        "url_query": conn.url.query or None,
        "user_agent": conn.headers.get("user-agent"),
        "trace_id": span and str(span.trace_id),
    }
    if error is not None:
        fields["event_outcome"] = EventOutcome.FAILURE
        fields["error_type"] = type(error).__name__
        fields["http_response_status_code"] = error.status_code
    return fields
