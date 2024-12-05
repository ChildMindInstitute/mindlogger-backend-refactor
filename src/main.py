import os
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from ddtrace.contrib.asgi.middleware import TraceMiddleware
from fastapi import FastAPI, Request, Response
from pydantic import parse_obj_as
from uvicorn.protocols.utils import get_path_with_query_string
import structlog
import time

from infrastructure.app import create_app
from infrastructure.logger import setup_logging

LOG_JSON_FORMAT = parse_obj_as(bool, os.getenv("LOG_JSON_FORMAT", False))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(json_logs=LOG_JSON_FORMAT, log_level=LOG_LEVEL)

app = create_app()


# @app.middleware("http")

#
# # This middleware must be placed after the logging, to populate the context with the request ID
# # NOTE: Why last??
# # Answer: middlewares are applied in the reverse order of when they are added (you can verify this
# # by debugging `app.middleware_stack` and recursively drilling down the `app` property).
# app.add_middleware(CorrelationIdMiddleware)


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
