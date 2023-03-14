from fastapi import Depends

from apps.authentication.deps import get_current_user
from apps.test_data.service import TestDataService


async def generate_test_data(user=Depends(get_current_user)) -> None:
    await TestDataService(user.id).create_applet()
