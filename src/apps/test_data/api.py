from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.test_data.domain import AnchorDateTime
from apps.test_data.service import TestDataService
from infrastructure.database import atomic, session_manager


async def generate_test_data(
    user=Depends(get_current_user),
    schema: AnchorDateTime = Body(default=AnchorDateTime()),
    session=Depends(session_manager.get_session),
) -> None:
    async with atomic(session):
        await TestDataService(session, user.id).create_applet(schema)
