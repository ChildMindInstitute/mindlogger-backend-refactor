import random
import string
from typing import Any, Awaitable, Callable

import pytest
from polyfactory import PostGenerated, Require, Use
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from sqlalchemy.orm import Session

from apps.users import User
from apps.users.domain import UserCreate
from apps.users.services.user import UserService


def generate_password() -> str:
    chars = (
        random.choices(string.ascii_uppercase, k=3)
        + random.choices(string.ascii_lowercase, k=3)
        + random.choices(string.digits, k=3)
        + random.choices("!@#$%^&*()-_=+", k=3)
    )

    random.shuffle(chars)
    return "".join(chars)


def make_email(name: str, values: dict[str, Any], *args: Any, **kwargs: Any) -> str:
    return f"{values['first_name'].lower()}.{values['last_name'].lower()}@getting.com"


@register_fixture
class UserFactory(ModelFactory[User]): ...


@register_fixture
class UserCreateFactory(ModelFactory[UserCreate]):
    first_name = Require()
    last_name = Require()
    # Generate email if not supplied in build()
    email = PostGenerated(make_email)
    # Generate password if not supplied in build()
    password = Use(generate_password)


@pytest.fixture
def user_create_service(db_session: Session) -> Callable[[UserCreate], Awaitable[User]]:
    """Factory fixture for creating users."""

    async def _saver(user_create: UserCreate) -> User:
        return await UserService(db_session).create_user(user_create, test_id=None)

    return _saver


@pytest.fixture
async def phineas_user(
    user_create_service: Callable[[UserCreate], Awaitable[User]], user_create_factory: type[UserCreateFactory]
) -> User:
    user = user_create_factory.build(first_name="Phineas", last_name="Flynn")
    return await user_create_service(user)


@pytest.fixture
async def ferb_user(
    user_create_service: Callable[[UserCreate], Awaitable[User]], user_create_factory: type[UserCreateFactory]
) -> User:
    user = user_create_factory.build(first_name="Ferb", last_name="Flynn")
    return await user_create_service(user)


@pytest.fixture
async def perry_user(
    user_create_service: Callable[[UserCreate], Awaitable[User]], user_create_factory: type[UserCreateFactory]
) -> User:
    user = user_create_factory.build(first_name="Perry", last_name="Platypus")
    return await user_create_service(user)


@pytest.fixture
async def doofenshmirtz_user(
    user_create_service: Callable[[UserCreate], Awaitable[User]], user_create_factory: type[UserCreateFactory]
) -> User:
    user = user_create_factory.build(first_name="Heinz", last_name="Doofenshmirtz")
    return await user_create_service(user)
