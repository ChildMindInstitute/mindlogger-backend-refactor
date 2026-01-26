import uuid
from typing import AsyncGenerator

import pytest
import typer
from sqlalchemy.ext.asyncio.session import AsyncSession
from typer.testing import CliRunner

from apps.applets.domain.applet_full import AppletFull
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import UsersCRUD
from apps.users.commands.manage import app as manage_app
from apps.users.domain import User, UserCreate
from apps.users.services.user import UserService
from infrastructure.database import atomic


class TestUsersManage:
    USER_EMAIL = "mindlogger@gettingcurious.com"
    USER_FIRSTNAME = "Not"
    USER_LASTNAME = "Mindlogger"

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.fixture
    def app(self) -> typer.Typer:
        return manage_app

    @pytest.fixture
    async def cli_user_create(self) -> UserCreate:
        return UserCreate(
            email=self.USER_EMAIL,
            password="Test1234!",
            first_name=self.USER_FIRSTNAME,
            last_name=self.USER_LASTNAME,
        )

    @pytest.fixture
    async def cli_subject_create(self, applet_one: AppletFull, tom: User) -> SubjectCreate:
        return SubjectCreate(
            applet_id=applet_one.id,
            email=self.USER_EMAIL,
            first_name=self.USER_FIRSTNAME,
            last_name=self.USER_LASTNAME,
            secret_user_id=f"{uuid.uuid4()}",
            creator_id=tom.id,
        )

    @pytest.fixture
    async def regular_user(self, cli_user_create: UserCreate, global_session: AsyncSession) -> AsyncGenerator[User]:
        """A valid regular user"""
        async with atomic(global_session):
            user = await UserService(global_session).create_user(cli_user_create)
        # await global_session.commit()
        yield user

        crud = UsersCRUD(global_session)
        await crud._delete(id=user.id)
        await global_session.commit()

    @pytest.fixture
    async def deleted_user(self, cli_user_create: UserCreate, global_session: AsyncSession) -> AsyncGenerator[User]:
        """A valid regular user"""
        crud = UsersCRUD(global_session)
        async with atomic(global_session):
            user = await UserService(global_session).create_user(cli_user_create)
            user.model_dump()
            crud._delete(id=user.id)
        # await global_session.commit()
        yield user

        crud = UsersCRUD(global_session)
        await crud._delete(id=user.id)
        await global_session.commit()

    @pytest.fixture
    async def regular_subject(
        self, regular_user: User, cli_subject_create: SubjectCreate, global_session: AsyncSession
    ) -> AsyncGenerator[Subject]:
        """A valid regular subject"""
        async with atomic(global_session):
            cli_subject_create.user_id = regular_user.id
            subject = await SubjectsService(global_session, cli_subject_create.user_id).create(cli_subject_create)

        # await global_session.commit()
        yield subject

        crud = SubjectsCrud(global_session)
        await crud._delete(id=subject.id)
        await global_session.commit()

    async def test_user_dne(self, app: typer.Typer, runner: CliRunner, regular_user: User) -> None:
        result = runner.invoke(
            app,
            [
                "soft-delete",
                "D00CB5DC-2D01-4228-8897-19AEBA110A86",
                "DA22D76E-3C2B-4004-96C0-D7B928C5B6B0",
                "no-ticket",
            ],
        )

        assert result.exit_code == 2
        assert "User does not exist" in result.output

    async def test_subject_dne(self, app: typer.Typer, runner: CliRunner, regular_user: User) -> None:
        result = runner.invoke(
            app,
            [
                "soft-delete",
                str(regular_user.id),
                "DA22D76E-3C2B-4004-96C0-D7B928C5B6B0",
                "no-ticket",
            ],
        )

        assert result.exit_code == 2
        assert "Found user" in result.output
        assert "Subject does not exist" in result.output

    async def test_soft_delete(
        self, app: typer.Typer, runner: CliRunner, regular_user: User, regular_subject: Subject, applet_one: AppletFull
    ) -> None:
        result = runner.invoke(
            app,
            [
                "soft-delete",
                "--yes",
                str(regular_user.id),
                str(applet_one.id),
                "no-ticket",
            ],
        )

        assert result.exit_code == 0
