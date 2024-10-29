import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityCreate
from apps.activity_flows.domain.flow_create import FlowCreate
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.base import AppletBase
from apps.applets.service import AppletService
from apps.users.domain import User
from test.factory.encryption_factory import build_encryption


async def create_applet(
    session: AsyncSession, user: User, activities: List[ActivityCreate], activity_flows: List[FlowCreate], **kwargs
) -> AppletFull:
    attrs = {
        "display_name": f"Test Applet {uuid.uuid4()}",
        "link": None,
        "require_login": False,
        "pinned_at": None,
        "retention_period": None,
        "stream_enabled": None,
        "stream_ip_address": "127.0.0.1",
        "stream_port": 2323,
        "encryption": build_encryption(),
    }
    attrs.update(kwargs)

    applet = await AppletService(session, user.id).create(
        AppletCreate(**AppletBase(**attrs).dict(), activities=activities, activity_flows=activity_flows)
    )
    await session.commit()

    return applet
