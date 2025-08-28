from datetime import datetime, timedelta, timezone

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio.session import AsyncSession

from apps.authentication.services import AuthenticationService
from apps.users import User


class UserFactory(ModelFactory):
    __model__ = User


class TestAuthenticationService:
    @pytest.fixture
    def old_user(self) -> User:
        user = UserFactory.build()
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
        user.last_seen_at = past

        return user

    @pytest.fixture
    def user_not_seen(self) -> User:
        user = UserFactory.build()
        user.last_seen_at = None

        return user

    @pytest.fixture
    def recent_user(self) -> User:
        user = UserFactory.build()
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
        user.last_seen_at = past

        return user

    async def test_update_user_last_seen_ok(self, session: AsyncSession, old_user: User, mocker: MockerFixture) -> None:
        mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")
        await AuthenticationService(session).update_last_seen_at(old_user)
        mock_.assert_awaited_once_with(old_user.id)

    async def test_update_user_last_seen_is_none(
        self, session: AsyncSession, user_not_seen: User, mocker: MockerFixture
    ) -> None:
        mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")

        await AuthenticationService(session).update_last_seen_at(user_not_seen)
        mock_.assert_awaited_once_with(user_not_seen.id)

    async def test_update_user_last_seen_too_soon(
        self, session: AsyncSession, recent_user: User, mocker: MockerFixture
    ) -> None:
        mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")
        await AuthenticationService(session).update_last_seen_at(recent_user)
        mock_.assert_not_awaited()
