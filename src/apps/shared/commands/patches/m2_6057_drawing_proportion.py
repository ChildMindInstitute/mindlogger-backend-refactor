import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_full import ActivityFull
from apps.activities.domain.response_values import DrawingProportion, DrawingValues
from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.service.applet import AppletService
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD

APPLETS = [
    "648c7d0b-8819-c112-0b4f-702900000000",  # MoBi Harlem 1
    "648c7d0f-8819-c112-0b4f-709c00000000",  # MoBi Harlem 2
    "33e7e63c-7b59-43d5-8ccb-3e89cb6d6560",  # MoBi Harlem 3
    "648c80cd-8819-c112-0b4f-728d00000000",  # MoBi Midtown 1
    "648c802c-8819-c112-0b4f-719b00000000",  # MoBi Midtown 2
    "16ca6f9e-aa0a-4da9-9f50-f299e0c0cf64",  # MoBi_Testing
]


def enable_proportion(activities: list[ActivityFull]) -> list[ActivityFull]:
    for activity in activities:
        for item in activity.items:
            if isinstance(item.response_values, DrawingValues):
                item.response_values.proportion = DrawingProportion(enabled=True)
    return activities


async def main(session: AsyncSession, *args, **kwargs):
    for applet_id in APPLETS:
        fake_user_id = uuid.uuid4()
        applet = await AppletService(session, fake_user_id).get_full_applet(uuid.UUID(applet_id))
        role = await UserAppletAccessCRUD(session).get_applet_owner(uuid.UUID(applet_id))
        fixed_activities = enable_proportion(applet.activities)
        activity_flows = []
        for flow in applet.activity_flows:
            items = []
            for flow_item in flow.items:
                activity = next(
                    filter(lambda a: a.id == flow_item.activity_id, fixed_activities),
                    None,
                )
                if not activity:
                    raise Exception(f"Activity {flow_item.activity_id} not found")
                item = ActivityFlowItemUpdate(id=flow_item.id, activity_key=activity.key)
                items.append(item)
            flow_update = FlowUpdate(
                id=flow.id,
                name=flow.name,
                description=flow.description,
                is_single_report=flow.is_single_report,
                hide_badge=flow.hide_badge,
                report_included_activity_name=flow.report_included_activity_name,
                report_included_item_name=flow.report_included_item_name,
                is_hidden=flow.is_hidden,
                items=items,
            )
            activity_flows.append(flow_update)
        update_values = AppletUpdate(
            display_name=applet.display_name,
            description=applet.description,
            about=applet.about,
            image=applet.image,
            watermark=applet.watermark,
            theme_id=applet.theme_id,
            link=applet.link,
            require_login=applet.require_login,
            pinned_at=applet.pinned_at,
            retention_period=applet.retention_period,
            retention_type=applet.retention_type,
            stream_enabled=applet.stream_enabled,
            encryption=applet.encryption,
            activities=fixed_activities,
            activity_flows=activity_flows,
        )

        await AppletService(session, role.owner_id).update(applet.id, update_values)
