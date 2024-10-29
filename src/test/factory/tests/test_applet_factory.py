import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.test import BaseTest
from test.factory.activity_factory import build_activity
from test.factory.activity_item_factory import build_single_select_activity_item
from test.factory.applet_factory import create_applet
from test.factory.user_factory import create_user


class TestAppletFactory(BaseTest):
    async def test_create_empty_applet(self, session: AsyncSession):
        user = await create_user(session)
        applet = await create_applet(session, user, [], [])
        assert applet
        assert applet.id
        assert len(applet.activities) == 0

    async def test_create_applet_with_activities(self, session: AsyncSession):
        user = await create_user(session)

        item_name = f"test_item{uuid.uuid4()}"
        single_select_item = build_single_select_activity_item(item_name)
        activity_name = f"test activity {uuid.uuid4()}"
        activity = build_activity(items=[single_select_item], name=activity_name)

        applet = await create_applet(session, user, [activity], [])
        assert len(applet.activities) == 1
        assert applet.activities[0].name == activity_name
        assert len(applet.activities[0].items) == 1
        assert applet.activities[0].items[0].name == item_name
