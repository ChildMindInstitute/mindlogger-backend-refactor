import uuid
from typing import AsyncGenerator

import pytest
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import UserCreate
from apps.users.services.user import UserService
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD


@pytest.fixture(scope="session", autouse=True)
def tom_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("tom@mindlogger.com"),
        password="Test1234!",
        first_name="Tom",
        last_name="Isaak",
    )


@pytest.fixture(scope="session", autouse=True)
async def tom(tom_create: UserCreate, global_session: AsyncSession) -> AsyncGenerator:
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1"),
            email=tom_create.hashed_email,
            email_encrypted=tom_create.email,
            first_name=tom_create.first_name,
            last_name=tom_create.last_name,
            hashed_password=tom_create.hashed_password,
        )
    )
    await global_session.commit()
    yield user
    await crud._delete(id=user.id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def lucy_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("lucy@gmail.com"),
        password="Test123",
        first_name="Lucy",
        last_name="Gabel",
    )


@pytest.fixture(scope="session", autouse=True)
async def lucy(lucy_create: UserCreate, global_session):
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa2"),
            email=lucy_create.hashed_email,
            email_encrypted=lucy_create.email,
            first_name=lucy_create.first_name,
            last_name=lucy_create.last_name,
            hashed_password=lucy_create.hashed_password,
        )
    )
    await global_session.commit()
    yield user
    await crud._delete(id=user.id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def bob_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("bob@gmail.com"),
        password="Test1234!",
        first_name="Bob",
        last_name="Martin",
    )


@pytest.fixture(scope="session", autouse=True)
async def bob(bob_create: UserCreate, global_session):
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa3"),
            email=bob_create.hashed_email,
            email_encrypted=bob_create.email,
            first_name=bob_create.first_name,
            last_name=bob_create.last_name,
            hashed_password=bob_create.hashed_password,
        )
    )
    await global_session.commit()
    yield user
    await crud._delete(id=user.id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def mike_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("mike@gmail.com"),
        password="Test1234",
        first_name="Mike",
        last_name="Samuel",
    )


@pytest.fixture(scope="session", autouse=True)
async def mike(mike_create: UserCreate, global_session):
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4"),
            email=mike_create.hashed_email,
            email_encrypted=mike_create.email,
            first_name=mike_create.first_name,
            last_name=mike_create.last_name,
            hashed_password=mike_create.hashed_password,
        )
    )
    await global_session.commit()
    yield user
    await crud._delete(id=user.id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def user_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("user@example.com"),
        password="Test1234!",
        first_name="user",
        last_name="test",
    )


@pytest.fixture(scope="session", autouse=True)
async def user(user_create: UserCreate, global_session: AsyncSession):
    """Use this fixture if you need for some test clean user without nothing."""
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            email=user_create.hashed_email,
            email_encrypted=user_create.email,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            hashed_password=user_create.hashed_password,
        )
    )
    await global_session.commit()
    yield user
    await crud._delete(id=user.id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def anonym(global_session):
    crud = UsersCRUD(global_session)
    await UserService(global_session).create_anonymous_respondent(
        uuid_=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa7")
    )
    await global_session.commit()
    yield
    await crud._delete(is_anonymous_respondent=True)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def superadmin(global_session):
    uuid_ = uuid.UUID("57b63dfa-5cee-4a53-a69e-0a35407e601d")
    crud = UsersCRUD(global_session)
    await UserService(global_session).create_superuser(uuid_=uuid_)
    await global_session.commit()
    yield
    await UserWorkspaceCRUD(global_session)._delete(user_id=uuid_)
    await crud._delete(is_super_admin=True)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def all_session_users(
    tom: UserSchema,
    lucy: UserSchema,
    bob: UserSchema,
    mike: UserSchema,
    user: UserSchema,
    anonym: UserSchema,
    superadmin: UserSchema,
) -> list[UserSchema]:
    return [tom, lucy, bob, mike, user, anonym, superadmin]
