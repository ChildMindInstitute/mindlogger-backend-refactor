import uuid

import pytest
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User, UserCreate
from apps.users.errors import UserNotFound
from apps.users.services.user import UserService


async def test_get_user_by_id(session: AsyncSession, user: User):
    srv = UserService(session)
    result = await srv.get(user.id)
    assert result == User.from_orm(user)


async def test_user_exists_by_id__user_does_not_exist(session: AsyncSession, uuid_zero: uuid.UUID):
    srv = UserService(session)
    with pytest.raises(UserNotFound):
        await srv.exists_by_id(uuid_zero)


async def test_get_user_by_email(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
):
    srv = UserService(session)
    result = await srv.get_by_email(user_create.email)
    assert result == User.from_orm(user)


async def test_create_super_user_admin__created_only_once(
    session: AsyncSession,
):
    srv = UserService(session)
    await srv.create_superuser()
    await srv.create_superuser()
    crud = UsersCRUD(session)
    count = await crud.count(is_super_admin=True)
    assert count == 1


async def test_create_anonymous_respondent__created_only_once(
    session: AsyncSession,
):
    srv = UserService(session)
    await srv.create_anonymous_respondent()
    await srv.create_anonymous_respondent()
    crud = UsersCRUD(session)
    count = await crud.count(is_anonymous_respondent=True)
    assert count == 1


async def test_create_user(session: AsyncSession):
    crud = UsersCRUD(session)
    srv = UserService(session)
    data = UserCreate(
        email=EmailStr("test@example.com"),
        first_name="first",
        last_name="last",
        password="pass",
    )
    user = await srv.create_user(data)
    assert user.first_name == data.first_name
    assert user.last_name == data.last_name
    assert user.email == data.hashed_email
    assert user.email_encrypted == data.email
    user_from_db = await crud.get_by_email(data.email)
    assert user_from_db.id == user.id
