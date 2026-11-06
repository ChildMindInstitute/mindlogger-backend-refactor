import uuid
from typing import AsyncGenerator

import pytest
import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession
from typer.testing import CliRunner

from apps.applets.domain.applet_full import AppletFull
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import UserSchema, UsersCRUD
from apps.users.commands.manage import NAME_CHECK
from apps.users.commands.manage import app as manage_app
from apps.users.db.schemas import UserDeviceSchema
from apps.users.domain import User, UserCreate, UserDeviceCreate
from apps.users.services.user import UserService
from apps.users.services.user_device import UserDeviceService
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic


class TestUsersManage:
    USER_EMAIL = "mindlogger@gettingcurious.com"
    USER_DELETED_EMAIL = "deleted@gettingcurious.com"
    USER_FIRSTNAME = "Not"
    USER_LASTNAME = "Mindlogger"

    USER_DELETED_FIRSTNAME = f"{NAME_CHECK}-M4-1234"
    USER_DELETED_LASTNAME = f"{NAME_CHECK}-M4-1234"
    USER_DELETED_NICKNAME = f"{NAME_CHECK}-M4-1234"

    TICKET_ID = "no-ticket"

    EMAIL_CHECK_STRING = "removed.user"

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Typer CliRunner fixture"""
        return CliRunner()

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Typer app under test fixture"""
        return manage_app

    @pytest.fixture
    async def regular_user(self, global_session: AsyncSession) -> AsyncGenerator[User]:
        """A valid regular user"""

        user_create = UserCreate(
            email=self.USER_EMAIL,
            password="Test12345!",
            first_name=self.USER_FIRSTNAME,
            last_name=self.USER_LASTNAME,
        )

        async with atomic(global_session):
            user = await UserService(global_session).create_user(user_create)
        yield user

        async with atomic(global_session):
            crud = UsersCRUD(global_session)
            await crud._delete(id=user.id)

    @pytest.fixture
    async def deleted_user(self, global_session: AsyncSession) -> AsyncGenerator[User]:
        """A deleted regular user"""

        user_create = UserCreate(
            email=self.USER_DELETED_EMAIL,
            password="Test12345!",
            first_name=self.USER_DELETED_FIRSTNAME,
            last_name=self.USER_DELETED_LASTNAME,
        )

        crud = UsersCRUD(global_session)
        async with atomic(global_session):
            user = await UserService(global_session).create_user(user_create)
            schema = UserSchema(**user.model_dump())
            schema = await crud.update_by_id(user.id, schema)
            user = User.model_validate(schema)

        yield user

        async with atomic(global_session):
            await crud._delete(id=user.id)

    @pytest.fixture
    async def regular_subject(
        self, regular_user: User, tom: User, applet_one: AppletFull, global_session: AsyncSession
    ) -> AsyncGenerator[Subject]:
        """A valid regular subject"""

        subject_create = SubjectCreate(
            applet_id=applet_one.id,
            email=self.USER_EMAIL,
            first_name=self.USER_FIRSTNAME,
            last_name=self.USER_LASTNAME,
            secret_user_id=f"{uuid.uuid4()}",
            creator_id=tom.id,
            user_id=regular_user.id,
        )

        async with atomic(global_session):
            subject = await SubjectsService(global_session, regular_user.id).create(subject_create)

        # await global_session.commit()
        yield subject

        async with atomic(global_session):
            crud = SubjectsCrud(global_session)
            await crud._delete(id=subject.id)

    @pytest.fixture
    async def deleted_subject(
        self,
        deleted_user: User,
        tom: User,
        applet_one: AppletFull,
        global_session: AsyncSession,
    ) -> AsyncGenerator[Subject]:
        """A deleted regular subject"""

        subject_create = SubjectCreate(
            applet_id=applet_one.id,
            email=self.USER_DELETED_EMAIL,
            first_name=self.USER_DELETED_FIRSTNAME,
            last_name=self.USER_DELETED_LASTNAME,
            nickname=self.USER_DELETED_NICKNAME,
            secret_user_id=f"{uuid.uuid4()}",
            creator_id=tom.id,
            user_id=deleted_user.id,
        )
        crud = SubjectsCrud(global_session)
        async with atomic(global_session):
            subject = await SubjectsService(global_session, deleted_user.id).create(subject_create)
            schema = SubjectSchema(**subject.model_dump())
            schema.is_deleted = True
            schema = await crud.update(schema)
            subject = Subject.model_validate(schema)

        yield subject

        async with atomic(global_session):
            crud = SubjectsCrud(global_session)
            await crud._delete(id=subject.id)

    #####################################################################
    ## Tests
    #####################################################################

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
        self,
        app: typer.Typer,
        runner: CliRunner,
        regular_user: User,
        regular_subject: Subject,
        applet_one: AppletFull,
        global_session: AsyncSession,
    ) -> None:
        result = runner.invoke(
            app,
            [
                "soft-delete",
                "--yes",
                str(regular_user.id),
                str(applet_one.id),
                self.TICKET_ID,
            ],
        )

        assert result.exit_code == 0

        names = f"{NAME_CHECK}-{self.TICKET_ID}"

        user_crud = UsersCRUD(global_session)
        user = await user_crud._get("id", regular_user.id)
        assert user is not None
        assert user.first_name == names
        assert user.last_name == names
        assert self.EMAIL_CHECK_STRING in user.email
        assert self.EMAIL_CHECK_STRING in user.email_encrypted

        subject_crud = SubjectsCrud(global_session)
        subject = await subject_crud.get_by_id(regular_subject.id)
        assert subject is not None
        assert subject.first_name == names
        assert subject.last_name == names
        assert subject.nickname == names
        assert self.EMAIL_CHECK_STRING in subject.email

    async def test_soft_delete_user_already_deleted(
        self,
        app: typer.Typer,
        runner: CliRunner,
        deleted_user: User,
        regular_subject: Subject,
        applet_one: AppletFull,
        global_session: AsyncSession,
    ) -> None:
        result = runner.invoke(
            app,
            [
                "soft-delete",
                "--yes",
                str(deleted_user.id),
                str(applet_one.id),
                self.TICKET_ID,
            ],
        )

        assert result.exit_code == 2
        assert "User is already soft deleted" in result.output

    async def test_delete_orphaned(
        self, app: typer.Typer, runner: CliRunner, regular_user: User, global_session: AsyncSession
    ) -> None:
        async with atomic(global_session):
            await WorkspaceService(global_session, regular_user.id).create_workspace_from_user(regular_user)
            await UserDeviceService(global_session, regular_user.id).add_device(UserDeviceCreate(device_id="device"))

        result = runner.invoke(app, ["delete-orphaned", "--yes", self.USER_EMAIL])

        assert result.exit_code == 0
        for column in (UserSchema.id, UserWorkspaceSchema.user_id, UserDeviceSchema.user_id):
            rows = await global_session.execute(select(column).where(column == regular_user.id))
            assert rows.first() is None

    async def test_delete_orphaned_refuses_applet_member(
        self,
        app: typer.Typer,
        runner: CliRunner,
        regular_user: User,
        regular_subject: Subject,
        global_session: AsyncSession,
    ) -> None:
        result = runner.invoke(app, ["delete-orphaned", "--yes", self.USER_EMAIL])

        assert result.exit_code == 2
        assert "User is not orphaned: subjects.user_id" in result.output
        assert await UsersCRUD(global_session)._get("id", regular_user.id) is not None
