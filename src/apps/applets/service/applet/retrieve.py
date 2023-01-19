from apps.activities.crud import ActivitiesCRUD, ActivityItemsCRUD
from apps.activity_flows.crud import FlowItemsCRUD, FlowsCRUD
from apps.applets.crud import AppletsCRUD
from apps.applets.domain.applets import detail


async def retrieve_applet(user_id: int, applet_id: int) -> detail.Applet:
    applet_schema = await AppletsCRUD().get_by_id(applet_id)
    applet: detail.Applet = detail.Applet.from_orm(applet_schema)
    activity_schemas = await ActivitiesCRUD().get_by_applet_id(applet_id)
    activity_item_schemas = await ActivityItemsCRUD().get_by_applet_id(
        applet_id
    )
    flow_schemas = await FlowsCRUD().get_by_applet_id(applet_id)
    flow_item_schemas = await FlowItemsCRUD().get_by_applet_id(applet_id)

    activity_map: dict[int, detail.Activity] = dict()
    flow_map: dict[int, detail.ActivityFlow] = dict()

    for activity_schema in activity_schemas:
        activity = detail.Activity.from_orm(activity_schema)
        applet.activities.append(activity)
        activity_map[activity.id] = activity

    for activity_item_schema in activity_item_schemas:
        activity_map[activity_item_schema.activity_id].items.append(
            detail.ActivityItem.from_orm(activity_item_schema)
        )

    for flow_schema in flow_schemas:
        flow: detail.ActivityFlow = detail.ActivityFlow.from_orm(flow_schema)
        applet.activity_flows.append(flow)
        flow_map[flow.id] = flow

    for flow_item_schema in flow_item_schemas:
        flow_item: detail.ActivityFlowItem = detail.ActivityFlowItem.from_orm(
            flow_item_schema
        )
        flow_item.activity = activity_map[flow_item.activity_id]
        flow_map[flow_item_schema.activity_flow_id].items.append(flow_item)

    return applet
