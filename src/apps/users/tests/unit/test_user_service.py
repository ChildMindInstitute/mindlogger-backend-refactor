import uuid
from typing import cast

import pytest
from pydantic import EmailStr
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from apps.integrations.prolific.domain import ProlificParamsActivityAnswer
from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserCreate
from apps.users.errors import UserNotFound
from apps.users.services.prolific_user import ProlificUserService
from apps.users.services.user import UserService
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from config import settings


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


async def test_create_super_user_admin(session: AsyncSession):
    crud = UsersCRUD(session)
    await UserWorkspaceCRUD(session)._delete()
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


async def test_create_prolific_respondent(session: AsyncSession):
    crud = UsersCRUD(session)
    await crud._delete(is_prolific_respondent=true())

    srv = ProlificUserService(
        session,
        ProlificParamsActivityAnswer(
            prolific_pid="prolific_respondent_id", session_id="prolific_session_id", study_id="prolific_study_id"
        ),
    )
    prolific_respondent = await srv.create_prolific_respondent()
    assert prolific_respondent.is_prolific_respondent
    assert (
        prolific_respondent.email_encrypted
        == f"{srv.prolific_pid}-{srv.prolific_session_id}{settings.prolific_respondent.domain}"
    )
    assert prolific_respondent.first_name == settings.prolific_respondent.first_name
    assert prolific_respondent.last_name == settings.prolific_respondent.last_name


async def test_create_prolific_respondent__created_only_once(session: AsyncSession):
    srv1 = ProlificUserService(
        session,
        ProlificParamsActivityAnswer(
            prolific_pid="prolific_respondent_id", session_id="prolific_session_id", study_id="prolific_study_id"
        ),
    )
    srv2 = ProlificUserService(
        session,
        ProlificParamsActivityAnswer(
            prolific_pid="prolific_respondent_id", session_id="prolific_session_id", study_id="prolific_study_id"
        ),
    )

    await srv1.create_prolific_respondent()
    await srv2.create_prolific_respondent()
    crud = UsersCRUD(session)
    count = await crud.count(is_prolific_respondent=True)
    assert count == 1


async def test_create_two_different_sessions_prolific_respondent(session: AsyncSession):
    srv1 = ProlificUserService(
        session,
        ProlificParamsActivityAnswer(
            prolific_pid="prolific_respondent_id", session_id="prolific_session_id-1", study_id="prolific_study_id"
        ),
    )
    srv2 = ProlificUserService(
        session,
        ProlificParamsActivityAnswer(
            prolific_pid="prolific_respondent_id", session_id="prolific_session_id-2", study_id="prolific_study_id"
        ),
    )

    await srv1.create_prolific_respondent()
    await srv2.create_prolific_respondent()
    crud = UsersCRUD(session)
    count = await crud.count(is_prolific_respondent=True)
    assert count == 2


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


async def test_create_user_with_test_id(session: AsyncSession):
    id_ = uuid.uuid4()
    srv = UserService(session)
    data = UserCreate(
        email=EmailStr("test@example.com"),
        first_name="first",
        last_name="last",
        password="pass",
    )
    user = await srv.create_user(data, test_id=id_)
    assert user.id == id_
