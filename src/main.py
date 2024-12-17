import logging
import os

# Import DataDog tracer ASAP
if os.getenv("DD_TRACE_ENABLED", "false").lower() == "true":
    logging.getLogger("main").setLevel(logging.INFO)
    logging.getLogger("main").addHandler(logging.StreamHandler())
    logging.getLogger("main").info("Enabling Datadog")
    # import ddtrace.auto  # noqa
    from ddtrace import patch

    # Manually patch.  The auto patcher throws some errors in AMQP (which it doesn't support so why patch it??)
    patch(
        sqlalchemy=True,
        fastapi=True,
        botocore=True,
        asyncpg=True,
        httpx=True,
        jinja2=True,
        requests=True,
        starlette=True,
        structlog=True,
    )


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
