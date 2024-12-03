import os
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from ddtrace.contrib.asgi.middleware import TraceMiddleware
from fastapi import FastAPI, Request, Response
from pydantic import parse_obj_as
from uvicorn.protocols.utils import get_path_with_query_string
import structlog
import time

# Inject Datadog tracer ASAP
# if os.getenv("DD_TRACE_ENABLED", "false").lower() == 'true':
#     import ddtrace.auto

from infrastructure.app import create_app


app = create_app()

@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    # These context vars will be added to all log entries emitted during the request
    request_id = correlation_id.get()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.perf_counter_ns()
    # If the call_next raises an error, we still want to return our own 500 response,
    # so we can add headers to it (process time, request ID...)
    response = Response(status_code=500)
    try:
        response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
        raise
    finally:
        access_logger = structlog.stdlib.get_logger("api.access")
        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information

        if status_code > 400 and status_code < 500:
            access_logger.warn(
                f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
                http={
                    "url": str(request.url),
                    "status_code": status_code,
                    "method": http_method,
                    "request_id": request_id,
                    "version": http_version,
                },
                network={"client": {"ip": client_host, "port": client_port}},
                duration=process_time,
            )
        else:
            access_logger.info(
                f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
                http={
                    "url": str(request.url),
                    "status_code": status_code,
                    "method": http_method,
                    "request_id": request_id,
                    "version": http_version,
                },
                network={"client": {"ip": client_host, "port": client_port}},
                duration=process_time,
            )
        # response.headers["X-Process-Time"] = str(process_time / 10 ** 9)
        return response


# This middleware must be placed after the logging, to populate the context with the request ID
# NOTE: Why last??
# Answer: middlewares are applied in the reverse order of when they are added (you can verify this
# by debugging `app.middleware_stack` and recursively drilling down the `app` property).
app.add_middleware(CorrelationIdMiddleware)

# UGLY HACK
# Datadog's `TraceMiddleware` is applied as the very first middleware in the list, by patching `FastAPI` constructor.
# Unfortunately that means that it is the innermost middleware, so the trace/span are created last in the middleware
# chain. Because we want to add the trace_id/span_id in the access log, we need to extract it from the middleware list,
# put it back as the outermost middleware, and rebuild the middleware stack.
tracing_middleware = next(
    (m for m in app.user_middleware if m.cls == TraceMiddleware), None
)
if tracing_middleware is not None:
    app.user_middleware = [m for m in app.user_middleware if m.cls != TraceMiddleware]
    structlog.stdlib.get_logger("api.datadog_patch").info(
        "Patching Datadog tracing middleware to be the outermost middleware..."
    )
    app.user_middleware.insert(0, tracing_middleware)
    app.middleware_stack = app.build_middleware_stack()

# @app.on_event("startup")
# async def create_superuser():
#     print("Create/Update superuser")
#     from apps.users.services.user import UserService
#     from infrastructure.database import atomic, session_manager
#
#     session = session_manager.get_session()
#
#     async with atomic(session):
#         await UserService(session).create_superuser()
