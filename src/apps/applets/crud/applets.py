import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

from apps.activities.crud import ActivitiesCRUD, ActivitiesHistoryCRUD, \
    ActivityItemsHistoryCRUD
from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activity_flows.crud import FlowsCRUD, FlowsHistoryCRUD, \
    FlowItemsHistoryCRUD
from apps.activity_flows.db.schemas import (
    ActivityFlowHistoriesSchema,
    ActivityFlowItemHistorySchema,
)
from apps.applets import errors
from apps.applets.crud import AppletHistoryCRUD
from apps.applets.db.schemas import (
    AppletHistorySchema,
    AppletSchema,
    UserAppletAccessSchema,
)
from apps.applets.domain.applets import Applet, AppletCreate, AppletUpdate
from apps.applets.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class AppletsCRUD(BaseCRUD[AppletSchema]):
    schema_class = AppletSchema
    initial_version = "1.0.0"
    version_difference = 0.01

    def _get_version(self, previous_version: str | None = None):
        if not previous_version:
            return self.initial_version
        v1, v2, v3 = list(map(int, previous_version.split(".")))
        v3 += 1
        v2 += v3 // 10
        v1 += v2 // 10
        v3 %= 10
        v2 %= 10
        return f"{v1}.{v2}.{v3}"

    async def _fetch(self, key: str, value: Any) -> Applet:
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

        # Get internal model
        applet: Applet = Applet.from_orm(instance)

        return applet

    async def get_by_id(self, id_: int) -> Applet:
        applet = await self._fetch(key="id", value=id_)
        return applet

    async def get_full_by_id(self, id_: int) -> Applet:
        applet = await self._fetch(key="id", value=id_)
        applet.activities = await ActivitiesCRUD().get_by_applet_id(id_)
        applet.activity_flows = await FlowsCRUD().get_by_applet_id(id_)
        return applet

    async def get_admin_applets(self, user_id_: int) -> list[Applet]:
        query = select(self.schema_class)
        query = query.join_from(UserAppletAccessSchema, self.schema_class)
        query = query.where(UserAppletAccessSchema.user_id == user_id_)
        query = query.where(UserAppletAccessSchema.role == Role.ADMIN)
        query = query.order_by(self.schema_class.id)
        result: Result = await self._execute(query)

        results: list[Applet] = result.scalars().all()

        return [Applet.from_orm(applet) for applet in results]

    async def save(self, user_id: int, schema: AppletCreate) -> Applet:
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

        applet: Applet = Applet.from_orm(instance)
        activity_map: dict[uuid.UUID, int] = dict()
        applet.activities = await ActivitiesCRUD().create_many(
            applet.id, schema.activities
        )
        for activity in applet.activities:
            activity_map[activity.guid] = activity.id

        applet.activity_flows = await FlowsCRUD().create_many(
            applet.id, schema.activity_flows, activity_map
        )
        await self._create_history(applet, instance.creator_id, instance.account_id)
        return applet

    async def delete_by_id(self, id_: int):
        """Delete applets by id."""

        await self._delete(key="id", value=id_)

    async def update_applet(
            self, user_id: int, pk: int, schema: AppletUpdate
    ) -> Applet:
        applet: Applet = await self.get_by_id(pk)
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
        applet = Applet.from_orm(instance)

        applet.activities = await ActivitiesCRUD().update_many(
            applet.id, schema.activities
        )

        activity_map: dict[uuid.UUID, int] = dict()
        for activity in applet.activities:
            activity_map[activity.guid] = activity.id

        applet.activity_flows = await FlowsCRUD().update_many(
            applet.id, schema.activity_flows, activity_map
        )
        await self._create_history(applet, user_id, user_id)
        return applet

    async def _create_history(
            self, applet: Applet, creator_id: int, account_id: int
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
        activities = []
        activity_items = []
        activity_flows = []
        activity_flow_items = []

        for activity in applet.activities:
            activity_id_version = f"{activity.id}_{applet.version}"
            activities.append(
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

            for item in activity.items:
                item_id_version = f"{item.id}_{applet.version}"
                activity_items.append(
                    ActivityItemHistorySchema(
                        id=item.id,
                        id_version=item_id_version,
                        activity_id=item.activity_id,
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

        for flow in applet.activity_flows:
            flow_id_version = f"{flow.id}_{applet.version}"
            activity_flows.append(
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

            for item in flow.items:
                item_id_version = f"{item.id}_{applet.version}"
                activity_id_version = f"{item.activity_id}_{applet.version}"
                activity_flow_items.append(
                    ActivityFlowItemHistorySchema(
                        id_version=item_id_version,
                        id=item.id,
                        activity_flow_id=item.activity_flow_id,
                        activity_id=activity_id_version,
                        ordering=item.ordering,
                    )
                )
        await ActivitiesHistoryCRUD().create_many(activities)
        await ActivityItemsHistoryCRUD().create_many(activity_items)
        await FlowsHistoryCRUD().create_many(activity_flows)
        await FlowItemsHistoryCRUD().create_many(activity_flow_items)
