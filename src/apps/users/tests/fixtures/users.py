from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.services import AuthenticationService
from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import UserCreateRequest


@pytest.fixture
def user_tom_create() -> UserCreateRequest:
    # Use tom data for replacing json fixtures with pytest fixtures
    # without failing tests
    return UserCreateRequest(
        email="tom@mindlogger.com",
        password="Test1234!",
        first_name="Tom",
        last_name="Isaak",
    )


@pytest.fixture
async def user_tom(
    user_tom_create: UserCreateRequest, session: AsyncSession
) -> AsyncGenerator:
    email_hash = hash_sha224(user_tom_create.email)
    hashed_password = AuthenticationService.get_password_hash(
        user_tom_create.password
    )
    user = await UsersCRUD(session).save(
        UserSchema(
            email=email_hash,
            email_encrypted=user_tom_create.email,
            first_name=user_tom_create.first_name,
            last_name=user_tom_create.last_name,
            hashed_password=hashed_password,
        )
    )
    yield user
