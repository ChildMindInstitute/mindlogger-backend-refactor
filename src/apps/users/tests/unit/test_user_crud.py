import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.hashing import hash_sha224
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User, UserChangePassword, UserCreate, UserUpdateRequest
from apps.users.errors import UserAlreadyExistError, UserIsDeletedError, UserNotFound


async def test_get_user_by_id(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.get_by_id(tom.id)
    assert user.id == tom.id


async def test_get_user_by_id__user_does_not_exists(session: AsyncSession, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_id(uuid_zero)


async def test_get_user_by_id__user_deleted(session: AsyncSession, tom: UserSchema):
    crud = UsersCRUD(session)
    user_id = tom.id
    await crud.update_by_id(user_id, UserSchema(is_deleted=True))
    await session.commit()
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_id(user_id)


async def test_get_user_by_email(
    tom: UserSchema,
    session: AsyncSession,
    tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    user = await crud.get_by_email(tom_create.email)
    assert user.id == tom.id


async def test_get_user_by_email__user_does_not_exists(session: AsyncSession):
    crud = UsersCRUD(session)
    with pytest.raises(UserNotFound):
        await crud.get_by_email("doesnotexist@example.com")


async def test_get_user_by_email__user_deleted(
    session: AsyncSession,
    tom: UserSchema,
    tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    await crud.update_by_id(tom.id, UserSchema(is_deleted=True))
    await session.commit()
    with pytest.raises(UserIsDeletedError):
        await crud.get_by_email(tom_create.email)


async def test_create_user_minimal_data(tom_create: UserCreate, session: AsyncSession):
    crud = UsersCRUD(session)
    user = await crud.save(
        UserSchema(
            hashed_password=tom_create.password,
            last_name=tom_create.last_name,
            first_name=tom_create.first_name,
        )
    )
    assert user.email_encrypted is None
    # Interesting case
    assert user.email is None
    assert user.first_name == tom_create.first_name
    assert user.last_name == tom_create.last_name
    assert not user.is_super_admin
    assert not user.is_anonymous_respondent
    assert not user.is_legacy_deleted_respondent


async def test_create_user__user_already_exists(tom_create: UserCreate, session: AsyncSession, tom: UserSchema):
    crud = UsersCRUD(session)
    with pytest.raises(UserAlreadyExistError):
        await crud.save(
            UserSchema(
                hashed_password=tom_create.password,
                last_name=tom_create.last_name,
                first_name=tom_create.first_name,
                email=hash_sha224(tom_create.email),
            )
        )


async def test_update_user(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    data = UserUpdateRequest(first_name="new", last_name="new")
    user = await crud.update(User.from_orm(tom), data)
    await session.commit()
    assert user.first_name == data.first_name
    assert user.last_name == data.last_name


async def test_update_user_by_id(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_first_name = "new"
    user = await crud.update_by_id(tom.id, UserSchema(first_name=new_first_name))
    assert user.first_name == new_first_name


async def test_update_encrypted_email(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_email = "newemail@example.com"
    user = await crud.update_encrypted_email(User.from_orm(tom), new_email)
    assert user.email_encrypted == new_email


async def test_delete_user__soft_delete(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    deleted = await crud.delete(tom.id)
    assert deleted.is_deleted


async def test_change_password(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    new_password = "newpassword"
    user_id = tom.id
    assert tom.hashed_password != new_password
    await crud.change_password(
        User.from_orm(tom),
        UserChangePassword(hashed_password=new_password),
    )
    await session.commit()
    user = await crud._get("id", user_id)
    user = cast(UserSchema, user)
    assert user.hashed_password == new_password


async def test_update_last_seet_at(
    faketime,
    tom: UserSchema,
    session: AsyncSession,
):
    crud = UsersCRUD(session)
    user_id = tom.id
    assert tom.last_seen_at != faketime.current_utc
    await crud.update_last_seen_by_id(tom.id)
    await session.commit()
    user = await crud._get("id", user_id)
    user = cast(UserSchema, user)
    assert user.last_seen_at == faketime.current_utc


async def test_user_exists_by_id(tom: UserSchema, session: AsyncSession):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(tom.id)
    assert result


async def test_user_exists_by_id__user_does_not_exist(
    session: AsyncSession,
    uuid_zero: uuid.UUID,
    tom: UserSchema,
):
    crud = UsersCRUD(session)
    result = await crud.exist_by_id(uuid_zero)
    assert not result


async def test_user_exists_by_id__user_deleted(session: AsyncSession, tom: UserSchema):
    crud = UsersCRUD(session)
    await crud.update_by_id(tom.id, UserSchema(is_deleted=True))
    result = await crud.exist_by_id(tom.id)
    assert not result


async def test_get_super_admin(session: AsyncSession, tom: UserSchema):
    crud = UsersCRUD(session)
    user = await crud.get_super_admin()
    user = cast(UserSchema, user)
    assert user.is_super_admin


async def test_get_users_by_ids__no_user_with_id(session: AsyncSession, tom: UserSchema, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero])
    assert not result


async def test_get_users_by_ids(session: AsyncSession, tom: UserSchema, uuid_zero: uuid.UUID):
    crud = UsersCRUD(session)
    result = await crud.get_by_ids([uuid_zero, tom.id])
    assert len(result) == 1


async def test_get_user_by_email_or_none__user_does_not_exist(
    session: AsyncSession,
    tom: UserSchema,
):
    crud = UsersCRUD(session)
    user = await crud.get_user_or_none_by_email("doesnotexist@example.com")
    assert user is None


async def test_get_user_by_email_or_none(
    session: AsyncSession,
    tom: UserSchema,
    tom_create: UserCreate,
):
    crud = UsersCRUD(session)
    user = await crud.get_user_or_none_by_email(tom_create.email)
    user = cast(UserSchema, user)
    assert user.id == tom.id
