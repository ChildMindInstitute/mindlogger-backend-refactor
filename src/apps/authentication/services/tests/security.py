from datetime import datetime, timedelta, timezone

from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio.session import AsyncSession

from apps.authentication.services import AuthenticationService
from apps.users import User


async def test_update_user_last_seen_ok(session: AsyncSession, user: User, mocker: MockerFixture):
    mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
    user.last_seen_at = past

    await AuthenticationService(session).update_last_seen_at(user)

    mock_.assert_awaited_once_with(user.id)


async def test_update_user_last_seen_is_none(session: AsyncSession, user: User, mocker: MockerFixture):
    mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")
    user.last_seen_at = None

    await AuthenticationService(session).update_last_seen_at(user)

    mock_.assert_awaited_once_with(user.id)


async def test_update_user_last_seen_too_soon(session: AsyncSession, user: User, mocker: MockerFixture):
    mock_ = mocker.patch("apps.users.cruds.user.UsersCRUD.update_last_seen_by_id")
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
    user.last_seen_at = past

    await AuthenticationService(session).update_last_seen_at(user)

    mock_.assert_not_awaited()
