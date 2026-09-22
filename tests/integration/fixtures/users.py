import uuid
from uuid import UUID

import pytest
import random
import string

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from sqlalchemy.orm import Session

from apps.users import User
from apps.users.domain import UserCreate
from apps.users.services.user import UserService
from infrastructure.database import atomic


@register_fixture
class UserFactory(ModelFactory[User]): ...

@register_fixture
class UserCreateFactory(ModelFactory[UserCreate]): ...



def generate_password() -> str:
    chars = (
        random.choices(string.ascii_uppercase, k=3)
        + random.choices(string.ascii_lowercase, k=3)
        + random.choices(string.digits, k=3)
        + random.choices("!@#$%^&*()-_=+", k=3)
    )

    random.shuffle(chars)
    return "".join(chars)


async def _create_user(db_session: Session, user_create_factory: type[UserCreateFactory], name: str, test_id: UUID = uuid.uuid4()) -> User:
    user = user_create_factory.build(password=generate_password(), email=f"{name}@gettingcurious.com")
    async with atomic(db_session):
        return await UserService(db_session).create_user(user, test_id=test_id)


@pytest.fixture
async def phineas_user(db_session: Session, user_create_factory: type[UserCreateFactory]):
    user = await _create_user(db_session, user_create_factory, "phineas")
    return user


@pytest.fixture
async def ferb_user(db_session: Session, user_create_factory: type[UserCreateFactory]):
    user = await _create_user(db_session, user_create_factory, "ferb")
    return user

@pytest.fixture
async def perry_user(db_session: Session, user_create_factory: type[UserCreateFactory]):
    user = await _create_user(db_session, user_create_factory, "perry")
    return user

@pytest.fixture
async def doofenshmirtz_user(db_session: Session, user_create_factory: type[UserCreateFactory]):
    user = await _create_user(db_session, user_create_factory, "doofenshmirtz")
    return user