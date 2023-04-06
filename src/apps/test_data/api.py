from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.test_data.domain import AnchorDateTime
from apps.test_data.service import TestDataService
from infrastructure.database import atomic, session_manager


async def test_data_generate(
    user=Depends(get_current_user),
    schema: AnchorDateTime = Body(default=AnchorDateTime()),
    session=Depends(session_manager.get_session),
) -> None:
    async with atomic(session):
        await TestDataService(session, user.id).create_applet(schema)


async def test_data_delete_generated(
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> None:
    async with atomic(session):
        await TestDataService(session, user.id).delete_generated_applets()
