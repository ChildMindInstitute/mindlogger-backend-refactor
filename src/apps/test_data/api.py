from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.test_data.domain import AppletGeneration
from apps.test_data.service import TestDataService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def test_data_generate(
    user=Depends(get_current_user),
    schema: AppletGeneration = Body(...),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        await TestDataService(session, user.id).create_applet(schema)


async def test_data_delete_generated(
    user=Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        await TestDataService(session, user.id).delete_generated_applets()
