import uuid
from collections import defaultdict

from apps.activities.crud import (
    ActivitiesCRUD,
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
    ActivityItemsCRUD,
)
from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
    ActivityItemSchema,
    ActivitySchema,
)
from apps.activity_flows.crud import (
    FlowItemHistoriesCRUD,
    FlowItemsCRUD,
    FlowsCRUD,
    FlowsHistoryCRUD,
)
from apps.activity_flows.db.schemas import (
    ActivityFlowHistoriesSchema,
    ActivityFlowItemHistorySchema,
    ActivityFlowItemSchema,
    ActivityFlowSchema,
)
from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.applets.domain.applets import fetch, update
from apps.applets.errors import AppletAccessDenied
from apps.applets.service import UserAppletAccessService
from apps.schedule.service import ScheduleService
from apps.shared.version import get_next_version


async def update_applet(
    applet_id: uuid.UUID, data: update.AppletUpdate, user_id: uuid.UUID
) -> fetch.Applet:
    applet = await _validate(user_id, applet_id)
    await _delete_applet_items(applet_id)
    applet = await _update_applet(applet, data, user_id)
    activities, activity_items = await _create_activities(
        applet, data.activities
    )
    flows, flow_items = await _create_flows(
        applet, activities, data.activity_flows
    )
    await _add_history(
        user_id, user_id, applet, activities, activity_items, flows, flow_items
    )
    return applet


async def _validate(user_id: uuid.UUID, applet_id: uuid.UUID):
    applet_schema = await AppletsCRUD().get_by_id(applet_id)
    role = await UserAppletAccessService(user_id, applet_id).get_editors_role()
    if not role:
        raise AppletAccessDenied()
    return fetch.Applet.from_orm(applet_schema)


async def _delete_applet_items(applet_id: uuid.UUID):
    await FlowItemsCRUD().delete_by_applet_id(applet_id)
    await FlowsCRUD().delete_by_applet_id(applet_id)
    await ActivityItemsCRUD().delete_by_applet_id(applet_id)
    await ActivitiesCRUD().delete_by_applet_id(applet_id)


async def _update_applet(
    applet: fetch.Applet, update_data: update.AppletUpdate, user_id
) -> fetch.Applet:
    schema = await AppletsCRUD().update_by_id(
        applet.id,
        AppletSchema(
            display_name=update_data.display_name,
            description=update_data.description,
            about=update_data.about,
            image=update_data.image,
            watermark=update_data.watermark,
            theme_id=update_data.theme_id,
            version=get_next_version(applet.version),
            creator_id=user_id,
            account_id=user_id,
            report_server_ip=update_data.report_server_ip,
            report_public_key=update_data.report_public_key,
            report_recipients=update_data.report_recipients,
            report_include_user_id=update_data.report_include_user_id,
            report_include_case_id=update_data.report_include_case_id,
            report_email_body=update_data.report_email_body,
        ),
    )
    applet = fetch.Applet.from_orm(schema)
    return applet


async def _create_activities(
    applet: fetch.Applet, create_data: list[update.ActivityUpdate]
) -> tuple[list[fetch.Activity], list[fetch.ActivityItem]]:
    activity_schemas: list[ActivitySchema] = []
    activity_item_schemas: list[ActivityItemSchema] = []
    activity_to_items_map = defaultdict(list)

    # Save existing activities to avoid creating default schedules for them
    all_activities = [
        activity.id
        for activity in await ActivitiesCRUD().get_by_applet_id(applet.id)
    ]
    existing_activities = []

    for index, activity_data in enumerate(create_data):
        if activity_data.id:
            existing_activities.append(activity_data.id)

        activity_schemas.append(
            ActivitySchema(
                id=activity_data.id or None,
                applet_id=applet.id,
                guid=activity_data.guid,
                name=activity_data.name,
                description=activity_data.description,
                splash_screen=activity_data.splash_screen,
                image=activity_data.image,
                show_all_at_once=activity_data.show_all_at_once,
                is_skippable=activity_data.is_skippable,
                is_reviewable=activity_data.is_reviewable,
                response_is_editable=activity_data.response_is_editable,
                ordering=index + 1,
            )
        )
        for item_index, activity_item_data in enumerate(activity_data.items):
            activity_item_schema = ActivityItemSchema(
                id=activity_item_data.id or None,
                question=activity_item_data.question,
                response_type=activity_item_data.response_type,
                answers=activity_item_data.answers,
                color_palette=activity_item_data.color_palette,
                timer=activity_item_data.timer,
                has_token_value=activity_item_data.has_token_value,
                is_skippable=activity_item_data.is_skippable,
                has_alert=activity_item_data.has_alert,
                has_score=activity_item_data.has_score,
                is_random=activity_item_data.is_random,
                has_text_response=activity_item_data.has_text_response,
                ordering=item_index + 1,
                is_able_to_move_to_previous=(
                    activity_item_data.is_able_to_move_to_previous
                ),
            )
            activity_item_schemas.append(activity_item_schema)
            activity_to_items_map[activity_data.guid].append(
                activity_item_schema
            )

    activity_schemas = await ActivitiesCRUD().create_many(activity_schemas)
    activities = []

    # Create default events for new activities
    activity_ids = [
        activity_schema.id
        for activity_schema in activity_schemas
        if activity_schema.id is not None
    ]
    new_activity_ids = set(activity_ids) - set(existing_activities)
    deleted_activity_ids = set(all_activities) - set(existing_activities)
    await ScheduleService().delete_by_activity_ids(
        applet_id=applet.id, activity_ids=list(deleted_activity_ids)
    )
    if new_activity_ids:
        await ScheduleService().create_default_schedules(
            applet_id=applet.id,
            activity_ids=list(new_activity_ids),
            is_activity=True,
        )

    for activity_schema in activity_schemas:
        activities.append(fetch.Activity.from_orm(activity_schema))
        activity_item_schemas = activity_to_items_map[activity_schema.guid]
        for activity_item_schema in activity_item_schemas:
            activity_item_schema.activity_id = activity_schema.id

    activity_item_schemas = await ActivityItemsCRUD().create_many(
        activity_item_schemas
    )
    activity_items = [
        fetch.ActivityItem.from_orm(schema) for schema in activity_item_schemas
    ]
    return activities, activity_items


async def _create_flows(
    applet: fetch.Applet,
    activities: list[fetch.Activity],
    create_data: list[update.ActivityFlowUpdate],
) -> tuple[list[fetch.ActivityFlow], list[fetch.ActivityFlowItem]]:
    flow_schemas = []
    flow_item_schemas = []
    flow_to_items_map = defaultdict(list)
    activity_guid_id_map = dict(
        (activity.guid, activity.id) for activity in activities
    )

    # Save existing flows to avoid creating default schedules for them
    all_flows = [
        flow.id for flow in await FlowsCRUD().get_by_applet_id(applet.id)
    ]
    existing_flows = []
    for index, flow_data in enumerate(create_data):
        flow_guid = uuid.uuid4()
        if flow_data.id:
            existing_flows.append(flow_data.id)

        flow_schemas.append(
            ActivityFlowSchema(
                id=flow_data.id or None,
                name=flow_data.name,
                guid=flow_guid,
                description=flow_data.description,
                applet_id=applet.id,
                is_single_report=flow_data.is_single_report,
                hide_badge=flow_data.hide_badge,
                ordering=index + 1,
            )
        )
        for item_index, item in enumerate(flow_data.items):
            flow_item_schema = ActivityFlowItemSchema(
                id=item.id or None,
                activity_id=activity_guid_id_map[item.activity_guid],
                ordering=item_index + 1,
            )
            flow_item_schemas.append(flow_item_schema)
            flow_to_items_map[flow_guid].append(flow_item_schema)

    # Create default events for new flows
    flow_ids = [
        flow_schema.id
        for flow_schema in flow_schemas
        if flow_schema.id is not None
    ]
    new_flow_ids = set(flow_ids) - set(existing_flows)
    deleted_flows = set(all_flows) - set(existing_flows)

    await ScheduleService().delete_by_flow_ids(
        applet_id=applet.id, flow_ids=list(deleted_flows)
    )
    if new_flow_ids:
        await ScheduleService().create_default_schedules(
            applet_id=applet.id,
            activity_ids=list(new_flow_ids),
            is_activity=False,
        )

    flow_schemas = await FlowsCRUD().create_many(flow_schemas)
    flows = []
    for flow_schema in flow_schemas:
        flows.append(fetch.ActivityFlow.from_orm(flow_schema))
        for flow_item_schema in flow_to_items_map[flow_schema.guid]:
            flow_item_schema.activity_flow_id = flow_schema.id

    flow_item_schemas = await FlowItemsCRUD().create_many(flow_item_schemas)
    flow_items = [
        fetch.ActivityFlowItem.from_orm(schema) for schema in flow_item_schemas
    ]
    return flows, flow_items


async def _add_history(
    creator_id: uuid.UUID,
    account_id: uuid.UUID,
    applet: fetch.Applet,
    activities: list[fetch.Activity],
    activity_items: list[fetch.ActivityItem],
    flows: list[fetch.ActivityFlow],
    flow_items: list[fetch.ActivityFlowItem],
):
    applet_id_version = f"{applet.id}_{applet.version}"
    await AppletHistoriesCRUD().save(
        AppletHistorySchema(
            id_version=applet_id_version,
            id=applet.id,
            display_name=applet.display_name,
            description=applet.description,
            about=applet.about,
            image=applet.image,
            watermark=applet.watermark,
            theme_id=applet.theme_id,
            version=applet.version,
            creator_id=creator_id,
            account_id=account_id,
            report_server_ip=applet.report_server_ip,
            report_public_key=applet.report_public_key,
            report_recipients=applet.report_recipients,
            report_include_user_id=applet.report_include_user_id,
            report_include_case_id=applet.report_include_case_id,
            report_email_body=applet.report_email_body,
        )
    )
    activity_schemas = []
    activity_item_schemas = []
    activity_flow_schemas = []
    activity_flow_item_schemas = []

    for activity in activities:
        activity_id_version = f"{activity.id}_{applet.version}"
        activity_schemas.append(
            ActivityHistorySchema(
                id=activity.id,
                id_version=activity_id_version,
                applet_id=applet_id_version,
                name=activity.name,
                description=activity.description,
                splash_screen=activity.splash_screen,
                image=activity.image,
                show_all_at_once=activity.show_all_at_once,
                is_skippable=activity.is_skippable,
                is_reviewable=activity.is_reviewable,
                response_is_editable=activity.response_is_editable,
                ordering=activity.ordering,
            )
        )

    for item in activity_items:
        activity_id_version = f"{item.activity_id}_{applet.version}"
        item_id_version = f"{item.id}_{applet.version}"
        activity_item_schemas.append(
            ActivityItemHistorySchema(
                id=item.id,
                id_version=item_id_version,
                activity_id=activity_id_version,
                question=item.question,
                response_type=item.response_type,
                answers=item.answers,
                color_palette=item.color_palette,
                timer=item.timer,
                has_token_value=item.has_token_value,
                is_skippable=item.is_skippable,
                has_alert=item.has_alert,
                has_score=item.has_score,
                is_random=item.is_random,
                is_able_to_move_to_previous=item.is_able_to_move_to_previous,
                has_text_response=item.has_text_response,
                ordering=item.ordering,
            )
        )

    for flow in flows:
        flow_id_version = f"{flow.id}_{applet.version}"
        activity_flow_schemas.append(
            ActivityFlowHistoriesSchema(
                id_version=flow_id_version,
                id=flow.id,
                applet_id=applet_id_version,
                name=flow.name,
                guid=flow.guid,
                description=flow.description,
                is_single_report=flow.is_single_report,
                hide_badge=flow.hide_badge,
                ordering=flow.ordering,
            )
        )

    for f_item in flow_items:
        flow_id_version = f"{f_item.activity_flow_id}_{applet.version}"
        item_id_version = f"{f_item.id}_{applet.version}"
        activity_id_version = f"{f_item.activity_id}_{applet.version}"
        activity_flow_item_schemas.append(
            ActivityFlowItemHistorySchema(
                id_version=item_id_version,
                id=f_item.id,
                activity_flow_id=flow_id_version,
                activity_id=activity_id_version,
                ordering=f_item.ordering,
            )
        )
    await ActivityHistoriesCRUD().create_many(activity_schemas)
    await ActivityItemHistoriesCRUD().create_many(activity_item_schemas)
    await FlowsHistoryCRUD().create_many(activity_flow_schemas)
    await FlowItemHistoriesCRUD().create_many(activity_flow_item_schemas)
