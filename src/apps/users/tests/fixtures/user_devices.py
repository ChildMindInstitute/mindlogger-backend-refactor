import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain import User, UserDeviceCreate
from apps.users.services.user_device import UserDeviceService


@pytest.fixture(scope="session", autouse=True)
def device_id() -> str:
    return "deviceid"


@pytest.fixture(scope="session", autouse=True)
async def device_tom(tom: User, global_session: AsyncSession, device_id: str):
    service = UserDeviceService(global_session, tom.id)
    await service.add_device(UserDeviceCreate(device_id=device_id))
    await global_session.commit()
    yield device_id
    await service.remove_device(device_id)
    await global_session.commit()
