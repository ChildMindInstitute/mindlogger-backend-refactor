import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user_device import UserDevicesCRUD
from apps.users.db.schemas import UserDeviceSchema, UserSchema
from apps.users.services.user_device import UserDeviceService


@pytest.fixture
async def device_user_tom(
    user_tom: UserSchema, session: AsyncSession
) -> UserDeviceSchema | None:
    service = UserDeviceService(session, user_tom.id)
    await service.add_device("deviceid")
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", "deviceid")
    return device


async def test_add_user_device(user_tom: UserSchema, session: AsyncSession):
    service = UserDeviceService(session, user_tom.id)
    await service.add_device("deviceid")
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", "deviceid")
    assert device


async def test_remove_user_device(
    device_user_tom: UserDeviceSchema, session: AsyncSession
):
    service = UserDeviceService(session, device_user_tom.user_id)
    await service.remove_device(device_user_tom.device_id)
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", "deviceid")
    assert not device


async def test_add_user_device_previous_device_is_removed(
    device_user_tom: UserDeviceSchema, session: AsyncSession
):
    service = UserDeviceService(session, device_user_tom.user_id)
    await service.add_device("deviceid")
    crud = UserDevicesCRUD(session)
    count = await crud.count()
    assert count == 1
