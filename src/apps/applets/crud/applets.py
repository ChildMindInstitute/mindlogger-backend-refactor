import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

from apps.activities.crud.activity import ActivitiesCRUD
from apps.activities.crud.activity_history import ActivitiesHistoryCRUD
from apps.activities.crud.activity_item_history import ActivityItemsHistoryCRUD
from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activity_flows.crud import (
    FlowItemsHistoryCRUD,
    FlowsCRUD,
    FlowsHistoryCRUD,
)
from apps.activity_flows.db.schemas import (
    ActivityFlowHistoriesSchema,
    ActivityFlowItemHistorySchema,
)
from apps.applets import errors
from apps.applets.crud.applets_history import AppletHistoryCRUD
from apps.applets.db.schemas import (
    AppletHistorySchema,
    AppletSchema,
    UserAppletAccessSchema,
)
from apps.applets.domain import (
    creating_applet,
    detailing_applet,
    fetching_applet,
    updating_applet,
)
from apps.applets.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class AppletsCRUD(BaseCRUD[AppletSchema]):
    schema_class = AppletSchema
    initial_version = "1.0.0"
    version_difference = 1

    async def save(
        self, user_id: int, schema: creating_applet.AppletCreate
    ) -> fetching_applet.Applet:
        """Return applets instance and the created information."""

        try:
            instance: AppletSchema = await self._create(
                AppletSchema(
                    display_name=schema.display_name,
                    description=schema.description,
                    about=schema.about,
                    image=schema.image,
                    watermark=schema.watermark,
                    theme_id=schema.theme_id,
                    version=self._get_version(),
                    creator_id=user_id,
                    account_id=user_id,
                    report_server_ip=schema.report_server_ip,
                    report_public_key=schema.report_public_key,
                    report_recipients=schema.report_recipients,
                    report_include_user_id=schema.report_include_user_id,
                    report_include_case_id=schema.report_include_case_id,
                    report_email_body=schema.report_email_body,
                )
            )
        except IntegrityError:
            raise errors.AppletAlreadyExist()

        applet = fetching_applet.Applet.from_orm(instance)
        activity_map: dict[uuid.UUID, fetching_applet.Activity] = dict()
        activities, activity_items = await ActivitiesCRUD().create_many(
            applet.id, schema.activities
        )
        for activity in activities:
            activity_map[activity.guid] = activity

        flows, flow_items = await FlowsCRUD().create_many(
            applet.id, schema.activity_flows, activity_map
        )
        await self._create_history(
            applet,
            activities,
            activity_items,
            flows,
            flow_items,
            instance.creator_id,
            instance.account_id,
        )
        return applet

    async def update_applet(
        self, user_id: int, pk: int, schema: updating_applet.AppletUpdate
    ) -> fetching_applet.Applet:
        applet = await self.get_applet(pk)
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=AppletSchema(
                display_name=schema.display_name,
                description=schema.description,
                about=schema.about,
                image=schema.image,
                watermark=schema.watermark,
                theme_id=schema.theme_id,
                version=self._get_version(applet.version),
                creator_id=user_id,
                account_id=user_id,
                report_server_ip=schema.report_server_ip,
                report_public_key=schema.report_public_key,
                report_recipients=schema.report_recipients,
                report_include_user_id=schema.report_include_user_id,
                report_include_case_id=schema.report_include_case_id,
                report_email_body=schema.report_email_body,
            ),
        )
        applet = fetching_applet.Applet.from_orm(instance)
        await FlowsCRUD().clear_applet_flows(applet.id)
        await ActivitiesCRUD().clear_applet_activities(applet.id)

        activities, activity_items = await ActivitiesCRUD().update_many(
            applet.id, schema.activities
        )

        activity_map: dict[uuid.UUID, int] = dict()
        for activity in activities:
            activity_map[activity.guid] = activity.id

        flows, flow_items = await FlowsCRUD().update_many(
            applet.id, schema.activity_flows, activity_map
        )
        await self._create_history(
            applet,
            activities,
            activity_items,
            flows,
            flow_items,
            user_id,
            user_id,
        )
        return applet

    def _get_version(self, previous_version: str | None = None):
        if not previous_version:
            return self.initial_version
        v1, v2, v3 = list(map(int, previous_version.split(".")))
        v3 += self.version_difference
        v2 += v3 // 10
        v1 += v2 // 10
        v3 %= 10
        v2 %= 10
        return f"{v1}.{v2}.{v3}"

    async def _fetch(self, key: str, value: Any) -> AppletSchema:
        """Fetch applets by id or display_name from the database."""

        if key not in {"id", "display_name"}:
            raise errors.AppletsError(
                f"Can not make the looking up applets by {key} {value}"
            )

        # Get applets from the database
        if not (instance := await self._get(key, value)):
            raise errors.AppletNotFoundError(
                f"No such applets with {key}={value}."
            )

        return instance

    async def get_applet(self, applet_id: int) -> fetching_applet.Applet:
        instance = await self._fetch(key="id", value=applet_id)
        return fetching_applet.Applet.from_orm(instance)

    async def get_full(self, applet_id: int) -> detailing_applet.Applet:
        instance = await self._fetch(key="id", value=applet_id)
        applet = detailing_applet.Applet.from_orm(instance)
        (
            applet.activities,
            activity_map,
        ) = await ActivitiesCRUD().get_by_applet_id(applet_id)
        applet.activity_flows = await FlowsCRUD().get_by_applet_id(
            applet_id, activity_map
        )
        return applet

    async def get_admin_applets(
        self, user_id_: int
    ) -> list[detailing_applet.Applet]:
        query = select(AppletSchema)
        query = query.join_from(UserAppletAccessSchema, AppletSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id_)
        query = query.where(UserAppletAccessSchema.role == Role.ADMIN)
        query = query.order_by(AppletSchema.id)
        result: Result = await self._execute(query)

        results: list[AppletSchema] = result.scalars().all()

        return [detailing_applet.Applet.from_orm(applet) for applet in results]

    async def delete_by_id(self, id_: int):
        """Delete applets by id."""

        await self._delete(key="id", value=id_)

    async def _create_history(
        self,
        applet: fetching_applet.Applet,
        activities: list[fetching_applet.Activity],
        activity_items: list[fetching_applet.ActivityItem],
        flows: list[fetching_applet.ActivityFlow],
        flow_items: list[fetching_applet.ActivityFlowItem],
        creator_id: int,
        account_id: int,
    ):
        applet_id_version = f"{applet.id}_{applet.version}"
        await AppletHistoryCRUD().save(
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
                    guid=activity.guid,
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
                    is_able_to_move_to_previous=(
                        item.is_able_to_move_to_previous
                    ),
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
        await ActivitiesHistoryCRUD().create_many(activity_schemas)
        await ActivityItemsHistoryCRUD().create_many(activity_item_schemas)
        await FlowsHistoryCRUD().create_many(activity_flow_schemas)
        await FlowItemsHistoryCRUD().create_many(activity_flow_item_schemas)
