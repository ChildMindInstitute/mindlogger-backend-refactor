from apps.activities.crud import (
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
)
from apps.activity_flows.crud import FlowItemHistoriesCRUD, FlowsHistoryCRUD
from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.domain.applets.history_detail import (
    Activity,
    ActivityFlow,
    ActivityFlowItem,
    ActivityItem,
    Applet,
)


async def retrieve_applet_by_version(
    applet_id: int, version: str
) -> None | Applet:
    id_version = f"{applet_id}_{version}"

    applet_schema = await AppletHistoriesCRUD().retrieve_by_applet_version(
        id_version
    )
    if not applet_schema:
        return None
    activity_schemas = (
        await ActivityHistoriesCRUD().retrieve_by_applet_version(id_version)
    )
    activity_item_schemas = (
        await ActivityItemHistoriesCRUD().retrieve_by_applet_version(id_version)
    )
    flow_schemas = await FlowsHistoryCRUD().retrieve_by_applet_version(
        id_version
    )
    flow_item_schemas = (
        await FlowItemHistoriesCRUD().retrieve_by_applet_version(id_version)
    )
    applet = Applet.from_orm(applet_schema)

    activity_map: dict[str, Activity] = dict()
    flow_map: dict[str, ActivityFlow] = dict()

    for activity_schema in activity_schemas:
        activity = Activity.from_orm(activity_schema)
        applet.activities.append(activity)
        activity_map[activity.id_version] = activity

    for activity_item_schema in activity_item_schemas:
        activity_map[activity_item_schema.activity_id].items.append(
            ActivityItem.from_orm(activity_item_schema)
        )

    for flow_schema in flow_schemas:
        flow = ActivityFlow.from_orm(flow_schema)
        flow_map[flow.id_version] = flow
        applet.activity_flows.append(flow)

    for flow_item_schema in flow_item_schemas:
        flow_item = ActivityFlowItem.from_orm(flow_item_schema)
        flow_item.activity = activity_map[flow_item.activity_id]
        flow_map[flow_item.activity_flow_id].items.append(flow_item)
    return applet
