import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserChangePassword, UserCreate, UserUpdateRequest
from apps.users.errors import UserAlreadyExistError, UserIsDeletedError, UserNotFound


async def test_get_user_by_id(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    act = await crud.get_by_id(user.id)
    assert act.id == user.id


async def test_get_user_by_id__user_does_not_exists(session: AsyncSession, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_id(uuid_zero)


async def test_get_user_by_id__user_deleted(session: AsyncSession, user: User):
    crud = UsersCRUD(session)
    await crud.update_by_id(user.id, UserSchema(is_deleted=True))
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_id(user.id)


async def test_get_user_by_email(
    user: User,
    session: AsyncSession,
    user_create: UserCreate,
):
    crud = UsersCRUD(session)
    act = await crud.get_by_email(user_create.email)
    assert act.id == user.id


async def test_get_user_by_email__user_does_not_exists(session: AsyncSession):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_email("doesnotexist@example.com")


async def test_get_user_by_email__user_deleted(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
):
    crud = UsersCRUD(session)
    await crud.update_by_id(user.id, UserSchema(is_deleted=True))
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_email(user_create.email)


async def test_create_user_minimal_data(user_create: UserCreate, session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.save(
        UserSchema(
            hashed_password=user_create.password,
            last_name=user_create.last_name,
            first_name=user_create.first_name,
        )
    )
    assert user.email_encrypted is None
    # Interesting case
    assert user.email is None
    assert user.first_name == user_create.first_name
    assert user.last_name == user_create.last_name
    assert not user.is_super_admin
    assert not user.is_anonymous_respondent
    assert not user.is_legacy_deleted_respondent


async def test_create_user__user_already_exists(user_create: UserCreate, session: AsyncSession):
    crud = UsersCRUD(session)
    with pytest.raises(UserAlreadyExistError):
        await crud.save(
            UserSchema(
                hashed_password=user_create.password,
                last_name=user_create.last_name,
                first_name=user_create.first_name,
                email=hash_sha224(user_create.email),
            )
        )


async def test_update_user(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    data = UserUpdateRequest(first_name="new", last_name="new")
    updated = await crud.update(user, data)
    assert updated.first_name == data.first_name
    assert updated.last_name == data.last_name


async def test_update_user_by_id(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    new_first_name = "new"
    updated = await crud.update_by_id(user.id, UserSchema(first_name=new_first_name))
    assert updated.first_name == new_first_name


async def test_update_encrypted_email(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    new_email = "newemail@example.com"
    updated = await crud.update_encrypted_email(user, new_email)
    assert updated.email_encrypted == new_email


async def test_delete_user__soft_delete(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    deleted = await crud.delete(user.id)
    assert deleted.is_deleted


async def test_change_password(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    new_password = "newpassword"
    user_id = user.id
    assert user.hashed_password != new_password
    await crud.change_password(
        user,
        UserChangePassword(hashed_password=new_password),
    )
    updated = await crud._get("id", user_id)
    updated = cast(UserSchema, updated)
    assert updated.hashed_password == new_password


async def test_update_last_seen_at(
    faketime,
    user: User,
    session: AsyncSession,
):
    crud = UsersCRUD(session)
    user_db = await crud._get("id", user.id)
    user_db = cast(UserSchema, user_db)
    assert user_db.last_seen_at != faketime.current_utc
    await crud.update_last_seen_by_id(user.id)
    await session.commit()
    updated = await crud._get("id", user.id)
    updated = cast(UserSchema, updated)
    assert updated.last_seen_at == faketime.current_utc


async def test_user_exists_by_id(user: User, session: AsyncSession):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(user.id)
    assert result


async def test_user_exists_by_id__user_does_not_exist(
    session: AsyncSession,
    uuid_zero: uuid.UUID,
):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(uuid_zero)
    assert not result


async def test_user_exists_by_id__user_deleted(session: AsyncSession, user: User):
    crud = UsersCRUD(session)
    await crud.update_by_id(user.id, UserSchema(is_deleted=True))
    result = await crud.exist_by_id(user.id)
    assert not result


async def test_get_super_admin(session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.get_super_admin()
    user = cast(UserSchema, user)
    assert user.is_super_admin


async def test_get_users_by_ids__no_user_with_id(session: AsyncSession, user: User, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero])
    assert not result


async def test_get_users_by_ids(session: AsyncSession, user: User, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero, user.id])
    assert len(result) == 1


async def test_get_user_by_email_or_none__user_does_not_exist(session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.get_user_or_none_by_email("doesnotexist@example.com")
    assert user is None


async def test_get_user_by_email_or_none(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
):
    crud = UsersCRUD(session)
    user_db = await crud.get_user_or_none_by_email(user_create.email)
    user_db = cast(UserSchema, user_db)
    assert user_db.id == user.id


def test_user_get_full_name():
    user = UserSchema(first_name="John", last_name="Doe")
    assert user.get_full_name() == "John Doe"


def test_user_get_full_name__no_last_name():
    user = UserSchema(first_name="John")
    assert user.get_full_name() == "John"
