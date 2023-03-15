from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.test_data.domain import AnchorDateTime
from apps.test_data.service import TestDataService


async def generate_test_data(
    user=Depends(get_current_user),
    anchor_datetime: AnchorDateTime = Body(...),
) -> None:
    await TestDataService(user.id).create_applet(anchor_datetime)
