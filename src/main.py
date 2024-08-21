import os

# Inject Datadog tracer ASAP
if os.getenv("DD_TRACE_ENABLED", "false").lower() == 'true':
    import ddtrace.auto

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
