import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.users.db.schemas import UserSchema
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def user_reviewer_applet_one(
    user: UserSchema, session: AsyncSession, mocker: MockerFixture, applet_one: AppletFull, lucy: User
):
    srv = UserAppletAccessService(session, user.id, applet_one.id)
    mocker.patch(
        "apps.workspaces.service.user_applet_access.UserAppletAccessService._get_default_role_meta",
        return_value={"respondents": [str(lucy.id)]},
    )
    await srv.add_role(user.id, Role.REVIEWER)
