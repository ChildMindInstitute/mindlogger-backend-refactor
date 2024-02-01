from typing import AsyncGenerator

import pytest
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import UserCreate


@pytest.fixture
def user_tom_create() -> UserCreate:
    # Use tom data for replacing json fixtures with pytest fixtures
    # without failing tests
    return UserCreate(
        email=EmailStr("tom@mindlogger.com"),
        password="Test1234!",
        first_name="Tom",
        last_name="Isaak",
    )


@pytest.fixture
async def user_tom(user_tom_create: UserCreate, session: AsyncSession) -> AsyncGenerator:
    crud = UsersCRUD(session)
    # backward compatibility with current JSON fixtures
    user = await crud.get_user_or_none_by_email(user_tom_create.email)
    if not user:
        user = await crud.save(
            UserSchema(
                email=user_tom_create.hashed_email,
                email_encrypted=user_tom_create.email,
                first_name=user_tom_create.first_name,
                last_name=user_tom_create.last_name,
                hashed_password=user_tom_create.hashed_password,
            )
        )
    yield user
