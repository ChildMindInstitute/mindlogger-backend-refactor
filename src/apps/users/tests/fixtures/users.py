import uuid
from typing import AsyncGenerator

import pytest
from pydantic import EmailStr
from pytest import Config
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User, UserCreate
from apps.users.services.user import UserService
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD


async def _get_or_create_user(
    crud: UsersCRUD, create_data: UserCreate, global_session: AsyncSession, id_: uuid.UUID | None
) -> User:
    user_db = await crud.get_user_or_none_by_email(create_data.email)
    if not user_db:
        user = await UserService(global_session).create_user(create_data, test_id=id_)
        await global_session.commit()
    else:
        user = User.from_orm(user_db)
    return user


@pytest.fixture(scope="session", autouse=True)
def user_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("user@example.com"),
        password="Test1234!",
        first_name="user",
        last_name="test",
    )


@pytest.fixture(scope="session", autouse=True)
def tom_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("tom@mindlogger.com"),
        password="Test1234!",
        first_name="Tom",
        last_name="Isaak",
    )


@pytest.fixture(scope="session", autouse=True)
def lucy_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("lucy@gmail.com"),
        password="Test123",
        first_name="Lucy",
        last_name="Gabel",
    )


@pytest.fixture(scope="session", autouse=True)
def bob_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("bob@gmail.com"),
        password="Test1234!",
        first_name="Bob",
        last_name="Martin",
    )


@pytest.fixture(scope="session", autouse=True)
def mike_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("mike@gmail.com"),
        password="Test1234",
        first_name="Mike",
        last_name="Samuel",
    )


@pytest.fixture(scope="session", autouse=True)
def pit_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("pit@gmail.com"),
        password="Test1234",
        first_name="Pit",
        last_name="Mitch",
    )


@pytest.fixture(scope="session", autouse=True)
def kate_create() -> UserCreate:
    return UserCreate(email=EmailStr("kate@gmail.com"), password="Test1234", first_name="Kate", last_name="Manson")


@pytest.fixture(scope="session", autouse=True)
async def user(user_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    """Use this fixture if you need for some test clean user without nothing."""
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(crud, user_create, global_session, None)
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def tom(tom_create: UserCreate, global_session: AsyncSession, pytestconfig: Config) -> AsyncGenerator:
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, tom_create, global_session, uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def lucy(lucy_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, lucy_create, global_session, uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa2")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def bob(bob_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, bob_create, global_session, uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa3")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def mike(mike_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, mike_create, global_session, uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa4")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def pit(pit_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, pit_create, global_session, uuid.UUID("6cde911e-8a57-47c0-b6b2-685b3664f418")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def reviewer(global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud,
        UserCreate(
            email=EmailStr("reviewer@mail.com"),
            password="Test1234!",
            first_name="Reviewer",
            last_name="User",
        ),
        global_session,
        uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502f00"),
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def kate(kate_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, kate_create, global_session, uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa8")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def patric(kate_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    # todo: delete after rewriting subjects tests from json to pytest fixtures
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud,
        UserCreate(
            email=EmailStr("patric@mail.com"),
            password="Test1234",
            first_name="Patric",
            last_name="Davison",
        ),
        global_session,
        uuid.UUID("6a180cd9-db2b-4195-a5ac-30a8733dfb06"),
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def pit_bronson(kate_create: UserCreate, global_session: AsyncSession, pytestconfig: Config):
    # todo: delete after rewriting subjects tests from json to pytest fixtures
    crud = UsersCRUD(global_session)
    kate_create.last_name = "Pit"
    kate_create.first_name = "Bronson"
    kate_create.email = EmailStr("pitbronson@mail.com")
    user = await _get_or_create_user(
        crud, kate_create, global_session, uuid.UUID("965f1d93-e64a-4f67-b76b-8427f033a864")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def bill_bronson(global_session: AsyncSession, pytestconfig: Config):
    # todo: delete after rewriting subjects tests from json to pytest fixtures
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud,
        UserCreate(
            email=EmailStr("billbronson@mail.com"),
            password="Test1234!",
            first_name="Boll",
            last_name="Bronson",
        ),
        global_session,
        uuid.UUID("f17e92e9-d60b-4756-9ecf-74af5da05092"),
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def anonym(global_session: AsyncSession, pytestconfig: Config):
    crud = UsersCRUD(global_session)
    schema = await crud.get_anonymous_respondent()
    if not schema:
        await UserService(global_session).create_anonymous_respondent(
            test_id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa7")
        )
        schema = await crud.get_anonymous_respondent()
    user = User.from_orm(schema)
    await global_session.commit()
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(is_anonymous_respondent=True)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def superadmin(global_session: AsyncSession, pytestconfig: Config):
    id_ = uuid.UUID("57b63dfa-5cee-4a53-a69e-0a35407e601d")
    crud = UsersCRUD(global_session)
    schema = await crud.get_super_admin()
    if not schema:
        await UserService(global_session).create_superuser(test_id=id_)
        await global_session.commit()
        schema = await crud.get_super_admin()
    user = User.from_orm(schema)
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await UserWorkspaceCRUD(global_session)._delete(user_id=id_)
        await crud._delete(is_super_admin=True)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
async def all_session_users(
    user: User, tom: User, lucy: User, bob: User, mike: User, anonym: User, superadmin: User
) -> list[User]:
    return [user, tom, lucy, bob, mike, anonym, superadmin]
