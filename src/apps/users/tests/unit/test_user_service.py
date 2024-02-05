import uuid
from typing import cast

import pytest
from pydantic import EmailStr
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserCreate
from apps.users.errors import UserNotFound
from apps.users.services.user import UserService
from config import settings


async def test_get_user_by_id(session: AsyncSession, tom: UserSchema):
    srv = UserService(session)
    result = await srv.get(tom.id)
    assert result == User.from_orm(tom)


async def test_user_exists_by_id__user_does_not_exist(session: AsyncSession, uuid_zero: uuid.UUID):
    srv = UserService(session)
    with pytest.raises(UserNotFound):
        await srv.exists_by_id(uuid_zero)


async def test_get_user_by_email(
    session: AsyncSession,
    tom: UserSchema,
    tom_create: UserCreate,
):
    srv = UserService(session)
    result = await srv.get_by_email(tom_create.email)
    assert result == User.from_orm(tom)


async def test_create_super_user_admin(session: AsyncSession):
    crud = UsersCRUD(session)
    await crud._delete(is_super_admin=true())
    await session.commit()
    assert await crud.get_super_admin() is None
    srv = UserService(session)
    await srv.create_superuser()
    user = await UsersCRUD(session).get_super_admin()
    user = cast(UserSchema, user)
    assert user.email_encrypted == settings.super_admin.email
    assert user.first_name == settings.super_admin.first_name
    assert user.last_name == settings.super_admin.last_name
    assert user.is_super_admin
    assert user.email == hash_sha224(settings.super_admin.email)


async def test_create_super_user_admin__created_only_once(
    session: AsyncSession,
):
    srv = UserService(session)
    await srv.create_superuser()
    await srv.create_superuser()
    crud = UsersCRUD(session)
    count = await crud.count(is_super_admin=True)
    assert count == 1


async def test_create_anonymous_respondent(session: AsyncSession):
    crud = UsersCRUD(session)
    await crud._delete(is_anonymous_respondent=true())
    assert await crud.get_anonymous_respondent() is None
    srv = UserService(session)
    await srv.create_anonymous_respondent()
    user = await UsersCRUD(session).get_anonymous_respondent()
    user = cast(UserSchema, user)
    assert user.email_encrypted == settings.anonymous_respondent.email
    assert user.first_name == settings.anonymous_respondent.first_name
    assert user.last_name == settings.anonymous_respondent.last_name
    assert user.is_anonymous_respondent
    assert user.email == hash_sha224(settings.anonymous_respondent.email)


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
