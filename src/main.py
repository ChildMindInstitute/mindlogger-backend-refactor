import os
import logging

# This line needs to be run before any `ddtrace` import, to avoid sending traces
# in local dev environment (we don't have a Datadog agent configured locally, so
# it prints a stacktrace every time it tries to send a trace)
# os.environ["DD_TRACE_ENABLED"] = os.getenv("DD_TRACE_ENABLED", "false")  # noqa

# Import DataDog tracer ASAP
if os.getenv("DD_TRACE_ENABLED", "false").lower() == "true":
    logging.getLogger("main").setLevel(logging.INFO)
    logging.getLogger("main").addHandler(logging.StreamHandler())
    logging.getLogger("main").info("Enabling Datadog")
    # import ddtrace.auto  # noqa
#     import ddtrace
#     ddtrace.patch_all()

from infrastructure.app import create_app

app = create_app()

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
