import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserChangePassword, UserCreate, UserUpdateRequest
from apps.users.errors import UserAlreadyExistError, UserIsDeletedError, UserNotFound


async def test_get_user_by_id(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.get_by_id(user_tom.id)
    assert user.id == user_tom.id


async def test_get_user_by_id__user_does_not_exists(session: AsyncSession, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_id(uuid_zero)


async def test_get_user_by_id__user_deleted(session: AsyncSession, user_tom: UserSchema):
    crud = UsersCRUD(session)
    await crud.update_by_id(user_tom.id, UserSchema(is_deleted=True))
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_id(user_tom.id)


async def test_get_user_by_email(
    user_tom: UserSchema,
    session: AsyncSession,
    user_tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    user = await crud.get_by_email(user_tom_create.email)
    assert user.id == user_tom.id


async def test_get_user_by_email__user_does_not_exists(session: AsyncSession):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_email("doesnotexist@example.com")


async def test_get_user_by_email__user_deleted(
    session: AsyncSession,
    user_tom: UserSchema,
    user_tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    await crud.update_by_id(user_tom.id, UserSchema(is_deleted=True))
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_email(user_tom_create.email)


async def test_create_user_minimal_data(user_tom_create: UserCreate, session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.save(
        UserSchema(
            hashed_password=user_tom_create.password,
            last_name=user_tom_create.last_name,
            first_name=user_tom_create.first_name,
        )
    )
    assert user.email_encrypted is None
    # Interesting case
    assert user.email is None
    assert user.first_name == user_tom_create.first_name
    assert user.last_name == user_tom_create.last_name
    assert not user.is_super_admin
    assert not user.is_anonymous_respondent
    assert not user.is_legacy_deleted_respondent


async def test_create_user__user_already_exists(user_tom_create: UserCreate, session: AsyncSession, user_tom):
    crud = UsersCRUD(session)
    with pytest.raises(UserAlreadyExistError):
        await crud.save(
            UserSchema(
                hashed_password=user_tom_create.password,
                last_name=user_tom_create.last_name,
                first_name=user_tom_create.first_name,
                email=hash_sha224(user_tom_create.email),
            )
        )


async def test_update_user(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    data = UserUpdateRequest(first_name="new", last_name="new")
    user = await crud.update(User.from_orm(user_tom), data)
    assert user.first_name == data.first_name
    assert user.last_name == data.last_name


async def test_update_user_by_id(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_first_name = "new"
    user = await crud.update_by_id(user_tom.id, UserSchema(first_name=new_first_name))
    assert user.first_name == new_first_name


async def test_update_encrypted_email(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_email = "newemail@example.com"
    user = await crud.update_encrypted_email(User.from_orm(user_tom), new_email)
    assert user.email_encrypted == new_email


async def test_delete_user__soft_delete(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    deleted = await crud.delete(user_tom.id)
    assert deleted.is_deleted


async def test_change_password(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_password = "newpassword"
    assert user_tom.hashed_password != new_password
    await crud.change_password(
        User.from_orm(user_tom),
        UserChangePassword(hashed_password=new_password),
    )
    user = await crud._get("id", user_tom.id)
    user = cast(UserSchema, user)
    assert user.hashed_password == new_password


async def test_update_last_seet_at(
    faketime,
    user_tom: UserSchema,
    session: AsyncSession,
):
    crud = UsersCRUD(session)
    assert user_tom.last_seen_at != faketime.current_utc
    await crud.update_last_seen_by_id(user_tom.id)
    user = await crud._get("id", user_tom.id)
    user = cast(UserSchema, user)
    assert user.last_seen_at == faketime.current_utc


async def test_user_exists_by_id(user_tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(user_tom.id)
    assert result


async def test_user_exists_by_id__user_does_not_exist(
    session: AsyncSession,
    uuid_zero: uuid.UUID,
    user_tom: UserSchema,
):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(uuid_zero)
    assert not result


async def test_user_exists_by_id__user_deleted(session: AsyncSession, user_tom: UserSchema):
    crud = UsersCRUD(session)
    await crud.update_by_id(user_tom.id, UserSchema(is_deleted=True))
    result = await crud.exist_by_id(user_tom.id)
    assert not result


async def test_get_super_admin(session: AsyncSession, user_tom: UserSchema):
    crud = UsersCRUD(session)
    none = await crud.get_super_admin()
    assert none is None
    await crud.update_by_id(user_tom.id, UserSchema(is_super_admin=True))
    user = await crud.get_super_admin()
    user = cast(UserSchema, user)
    assert user.id == user_tom.id


async def test_get_users_by_ids__no_user_with_id(session: AsyncSession, user_tom: UserSchema, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero])
    assert not result


async def test_get_users_by_ids(session: AsyncSession, user_tom: UserSchema, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero, user_tom.id])
    assert len(result) == 1


async def test_get_user_by_email_or_none__user_does_not_exist(
    session: AsyncSession,
    user_tom: UserSchema,
):
    crud = UsersCRUD(session)
    user = await crud.get_user_or_none_by_email("doesnotexist@example.com")
    assert user is None


async def test_get_user_by_email_or_none(
    session: AsyncSession,
    user_tom: UserSchema,
    user_tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    user = await crud.get_user_or_none_by_email(user_tom_create.email)
    user = cast(UserSchema, user)
    assert user.id == user_tom.id
