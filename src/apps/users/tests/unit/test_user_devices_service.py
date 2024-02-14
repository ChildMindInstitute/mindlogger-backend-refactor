import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user_device import UserDevicesCRUD
from apps.users.db.schemas import UserDeviceSchema
from apps.users.domain import User
from apps.users.services.user_device import UserDeviceService


@pytest.fixture
def device_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
async def device_user(user: User, session: AsyncSession, device_id: str) -> UserDeviceSchema | None:
    service = UserDeviceService(session, user.id)
    await service.add_device(device_id)
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", device_id)
    return device


async def test_add_user_device(user: User, session: AsyncSession, device_id: str):
    service = UserDeviceService(session, user.id)
    await service.add_device(device_id)
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", device_id)
    assert device


async def test_remove_user_device(device_user: UserDeviceSchema, session: AsyncSession, device_id: str):
    service = UserDeviceService(session, device_user.user_id)
    await service.remove_device(device_user.device_id)
    crud = UserDevicesCRUD(session)
    device = await crud._get("device_id", device_id)
    assert not device


async def test_add_user_device_previous_device_is_removed(
    device_user: UserDeviceSchema, session: AsyncSession, device_id: str, user: User
):
    service = UserDeviceService(session, device_user.user_id)
    await service.add_device(device_id)
    crud = UserDevicesCRUD(session)
    count = await crud.count(user_id=user.id)
    assert count == 1
