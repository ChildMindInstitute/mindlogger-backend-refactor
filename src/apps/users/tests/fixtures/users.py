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
    # Use tom data for replacing json fixtures with pytest fixtures
    # without failing tests
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
    user_id: uuid.UUID
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
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
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
    user_id: uuid.UUID
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
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
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
    user_id: uuid.UUID
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
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def patric_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("patric@gmail.com"),
        password="Test1234",
        first_name="Patric",
        last_name="Davidson",
    )


@pytest.fixture(scope="session", autouse=True)
async def patric(patric_create: UserCreate, global_session):
    user_id: uuid.UUID
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa5"),
            email=patric_create.hashed_email,
            email_encrypted=patric_create.email,
            first_name=patric_create.first_name,
            last_name=patric_create.last_name,
            hashed_password=patric_create.hashed_password,
        )
    )
    await global_session.commit()
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def mike2_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("mike2@gmail.com"),
        password="Test1234",
        first_name="Mike2",
        last_name="Samuel",
    )


@pytest.fixture(scope="session", autouse=True)
async def mike2(mike2_create: UserCreate, global_session):
    user_id: uuid.UUID
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa6"),
            email=mike2_create.hashed_email,
            email_encrypted=mike2_create.email,
            first_name=mike2_create.first_name,
            last_name=mike2_create.last_name,
            hashed_password=mike2_create.hashed_password,
        )
    )
    await global_session.commit()
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
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
def reviewer_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("reviewer@mail.com"),
        password="Test1234!",
        first_name="reviewer",
        last_name="ReviewerOne",
    )


@pytest.fixture(scope="session", autouse=True)
async def reviewer(reviewer_create: UserCreate, global_session):
    user_id: uuid.UUID
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502f00"),
            email=reviewer_create.hashed_email,
            email_encrypted=reviewer_create.email,
            first_name=reviewer_create.first_name,
            last_name=reviewer_create.last_name,
            hashed_password=reviewer_create.hashed_password,
        )
    )
    await global_session.commit()
    user_id = user.id
    yield user
    await crud._delete(id=user_id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def ivan_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("ivan@mindlogger.com"),
        password="Test1234!",
        first_name="Ivan",
        last_name="K",
    )


@pytest.fixture(scope="session", autouse=True)
async def ivan(ivan_create: UserCreate, global_session):
    user_id: uuid.UUID
    crud = UsersCRUD(global_session)
    user = await crud.save(
        UserSchema(
            id=uuid.UUID("6cde911e-8a57-47c0-b6b2-685b3664f418"),
            email=ivan_create.hashed_email,
            email_encrypted=ivan_create.email,
            first_name=ivan_create.first_name,
            last_name=ivan_create.last_name,
            hashed_password=ivan_create.hashed_password,
        )
    )
    await global_session.commit()
    user_id = user.id
    await crud._delete(id=user_id)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def superadmin(global_session):
    uuid_ = uuid.UUID("57b63dfa-5cee-4a53-a69e-0a35407e601d")
    crud = UsersCRUD(global_session)
    await UserService(global_session).create_superuser(uuid_=uuid_)
    await global_session.commit()
    yield
    ws_crud = UserWorkspaceCRUD(global_session)
    await ws_crud._delete(user_id=uuid_)
    await crud._delete(is_super_admin=True)
    await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def all_users(tom, lucy, bob, mike, mike2, anonym, patric, reviewer, ivan, superadmin):
    pass
