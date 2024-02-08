import uuid

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.db.schemas import UserSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def user_reviewer_applet_one(user: UserSchema, session: AsyncSession, mocker: MockerFixture):
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1")
    srv = UserAppletAccessService(session, user.id, applet_id)
    mocker.patch(
        "apps.workspaces.service.user_applet_access.UserAppletAccessService._get_default_role_meta",
        return_value={"respondents": ["7484f34a-3acc-4ee6-8a94-fd7299502fa6"]},
    )
    await srv.add_role(user.id, Role.REVIEWER)
