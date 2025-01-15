import datadog  # noqa: F401
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
