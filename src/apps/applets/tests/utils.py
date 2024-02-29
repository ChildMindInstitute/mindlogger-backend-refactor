import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.crud.activity import ActivitiesCRUD
from apps.activities.crud.activity_history import ActivityHistoriesCRUD
from apps.activity_flows.crud.flow import FlowsCRUD
from apps.activity_flows.crud.flow_history import FlowsHistoryCRUD
from apps.activity_flows.crud.flow_item import FlowItemsCRUD
from apps.activity_flows.crud.flow_item_history import FlowItemHistoriesCRUD
from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.applets_history import AppletHistoriesCRUD
from apps.schedule.crud.events import EventCRUD
from apps.shared.version import INITIAL_VERSION
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD


async def teardown_applet(global_session: AsyncSession, applet_id: uuid.UUID, version: str = INITIAL_VERSION) -> None:
    await UserAppletAccessCRUD(global_session)._delete(applet_id=applet_id)
    await EventCRUD(global_session)._delete(applet_id=applet_id)
    await FlowItemsCRUD(global_session)._delete()
    await FlowItemHistoriesCRUD(global_session)._delete()
    await FlowsHistoryCRUD(global_session)._delete(applet_id=f"{applet_id}_{version}")
    await FlowsCRUD(global_session)._delete(applet_id=applet_id)
    await ActivityHistoriesCRUD(global_session)._delete(applet_id=f"{applet_id}_{version}")
    await ActivitiesCRUD(global_session)._delete(applet_id=applet_id)
    await AppletHistoriesCRUD(global_session)._delete(id=applet_id)
    await AppletsCRUD(global_session)._delete(id=applet_id)
    await global_session.commit()
