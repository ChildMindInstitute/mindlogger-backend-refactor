import asyncio
import uuid

from apps.activities.crud import ActivitiesCRUD, ActivityHistoriesCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.activities.domain.activity import (
    ActivityBaseInfo,
    ActivityDuplicate,
    ActivityLanguageWithItemsMobileDetailPublic,
    ActivityOrFlowBasicInfoInternal,
    ActivitySingleLanguageDetail,
    ActivitySingleLanguageWithItemsDetail,
)
from apps.activities.domain.activity_create import ActivityCreate, PreparedActivityItemCreate
from apps.activities.domain.activity_full import ActivityFull
from apps.activities.domain.activity_update import (
    ActivityReportConfiguration,
    ActivityUpdate,
    PreparedActivityItemUpdate,
)
from apps.activities.errors import ActivityAccessDeniedError, ActivityDoeNotExist
from apps.activities.services.activity_item import ActivityItemService
from apps.activity_assignments.service import ActivityAssignmentService
from apps.activity_flows.crud import FlowsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.schedule.crud.events import EventCRUD
from apps.schedule.domain.constants import EventType
from apps.schedule.service.schedule import ScheduleService
from apps.workspaces.domain.constants import Role
from infrastructure.logger import logger


class ActivityService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def create(self, applet_id: uuid.UUID, activities_create: list[ActivityCreate]) -> list[ActivityFull]:
        schemas = []
        activity_key_id_map: dict[uuid.UUID, uuid.UUID] = dict()
        activity_id_key_map: dict[uuid.UUID, uuid.UUID] = dict()
        prepared_activity_items = list()

        for index, activity_data in enumerate(activities_create):
            # Pull the activity_id from the activity_data if it exists, otherwise generate a new UUID
            # CLI seeded activity data may have an id
            activity_id = getattr(activity_data, "id") if hasattr(activity_data, "id") else uuid.uuid4()
            activity_key_id_map[activity_data.key] = activity_id
            activity_id_key_map[activity_id] = activity_data.key

            schema = ActivitySchema(
                id=activity_id,
                applet_id=applet_id,
                name=activity_data.name,
                description=activity_data.description,
                splash_screen=activity_data.splash_screen,
                image=activity_data.image,
                show_all_at_once=activity_data.show_all_at_once,
                is_skippable=activity_data.is_skippable,
                is_reviewable=activity_data.is_reviewable,
                response_is_editable=activity_data.response_is_editable,
                is_hidden=activity_data.is_hidden,
                scores_and_reports=activity_data.scores_and_reports.dict()
                if activity_data.scores_and_reports
                else None,
                subscale_setting=activity_data.subscale_setting.dict() if activity_data.subscale_setting else None,
                order=index + 1,
                report_included_item_name=activity_data.report_included_item_name,  # noqa: E501
                extra_fields=activity_data.extra_fields,
                performance_task_type=activity_data.performance_task_type,
                auto_assign=activity_data.auto_assign,
            )

            if hasattr(activity_data, "created_at"):
                schema.created_at = getattr(activity_data, "created_at")

            schemas.append(schema)

            for item in activity_data.items:
                prepared_activity_item = PreparedActivityItemCreate(
                    activity_id=activity_id,
                    question=item.question,
                    response_type=item.response_type,
                    response_values=item.response_values.dict() if item.response_values else None,
                    config=item.config.dict(),
                    name=item.name,
                    is_hidden=item.is_hidden,
                    conditional_logic=item.conditional_logic.dict() if item.conditional_logic else None,
                    allow_edit=item.allow_edit,
                    extra_fields=item.extra_fields,
                )

                if hasattr(item, "created_at"):
                    prepared_activity_item.__dict__["created_at"] = getattr(item, "created_at")

                prepared_activity_items.append(prepared_activity_item)
        activity_schemas = await ActivitiesCRUD(self.session).create_many(schemas)
        activity_items = await ActivityItemService(self.session).create(prepared_activity_items)
        activities = list()

        activity_id_map: dict[uuid.UUID, ActivityFull] = dict()

        for activity_schema in activity_schemas:
            activity_schema.key = activity_id_key_map[activity_schema.id]
            activity = ActivityFull.from_orm(activity_schema)
            activities.append(activity)
            activity_id_map[activity.id] = activity

        for activity_item in activity_items:
            activity_id_map[activity_item.activity_id].items.append(activity_item)

        # add default schedule for activities
        await ScheduleService(self.session, admin_user_id=self.user_id).create_default_schedules(
            applet_id=applet_id,
            activity_ids=[activity.id for activity in activities if not activity.is_reviewable],
            is_activity=True,
        )

        return activities

    async def update_create(self, applet_id: uuid.UUID, activities_create: list[ActivityUpdate]) -> list[ActivityFull]:
        schemas = []
        activity_key_id_map: dict[uuid.UUID, uuid.UUID] = dict()
        activity_id_key_map: dict[uuid.UUID, uuid.UUID] = dict()
        prepared_activity_items = list()

        activity_events = await EventCRUD(self.session).get_by_type_and_applet_id(applet_id, EventType.ACTIVITY)

        all_activity_ids = [activity.activity_id for activity in activity_events if activity.activity_id is not None]

        # Save new activity ids
        new_activities = []
        existing_activities = []

        for index, activity_data in enumerate(activities_create):
            activity_id = activity_data.id or uuid.uuid4()
            activity_key_id_map[activity_data.key] = activity_id
            activity_id_key_map[activity_id] = activity_data.key

            if activity_data.id:
                existing_activities.append(activity_id)
            else:
                new_activities.append(activity_id)

            schemas.append(
                ActivitySchema(
                    id=activity_id,
                    applet_id=applet_id,
                    name=activity_data.name,
                    description=activity_data.description,
                    splash_screen=activity_data.splash_screen,
                    image=activity_data.image,
                    show_all_at_once=activity_data.show_all_at_once,
                    is_skippable=activity_data.is_skippable,
                    is_reviewable=activity_data.is_reviewable,
                    response_is_editable=activity_data.response_is_editable,
                    is_hidden=activity_data.is_hidden,
                    scores_and_reports=activity_data.scores_and_reports.dict()
                    if activity_data.scores_and_reports
                    else None,
                    subscale_setting=activity_data.subscale_setting.dict() if activity_data.subscale_setting else None,
                    order=index + 1,
                    report_included_item_name=(activity_data.report_included_item_name),
                    performance_task_type=activity_data.performance_task_type,
                    auto_assign=activity_data.auto_assign,
                )
            )

            for item in activity_data.items:
                if item.name in ["age_screen", "gender_screen"] and item.id is None:
                    # Implement logging for the age_screen and gender_screen items to trigger alerts
                    # in Datadog for the Greek version of the applet after translations were rolled back.
                    # TODO: Remove when full Greek support is available in Admin Panel [M2-8678](https://mindlogger.atlassian.net/browse/M2-8678)
                    logger.info(  # type: ignore
                        f"Creating {item.name} item for activity {activity_id} in applet_id {applet_id}",
                        applet_id=str(applet_id),
                        operation=f"update_{item.name}",
                    )

                prepared_activity_items.append(
                    PreparedActivityItemUpdate(
                        id=item.id or uuid.uuid4(),
                        name=item.name,
                        activity_id=activity_id,
                        question=item.question,
                        response_type=item.response_type,
                        response_values=item.response_values.dict() if item.response_values else None,
                        config=item.config.dict(),
                        conditional_logic=item.conditional_logic.dict() if item.conditional_logic else None,
                        allow_edit=item.allow_edit,
                        is_hidden=item.is_hidden,
                    )
                )
        activity_schemas = await ActivitiesCRUD(self.session).create_many(schemas)
        activity_items = await ActivityItemService(self.session).update_create(prepared_activity_items)
        activities = list()

        activity_id_map: dict[uuid.UUID, ActivityFull] = dict()

        for activity_schema in activity_schemas:
            activity_schema.key = activity_id_key_map[activity_schema.id]
            activity = ActivityFull.from_orm(activity_schema)
            activities.append(activity)
            activity_id_map[activity.id] = activity

        for activity_item in activity_items:
            activity_id_map[activity_item.activity_id].items.append(activity_item)

        # Remove events for deleted activities
        deleted_activity_ids = set(all_activity_ids) - set(existing_activities)

        schedule_service = ScheduleService(self.session, admin_user_id=self.user_id)

        if deleted_activity_ids:
            await schedule_service.delete_by_activity_ids(applet_id=applet_id, activity_ids=list(deleted_activity_ids))
            await ActivityAssignmentService(self.session).delete_by_activity_or_flow_ids(list(deleted_activity_ids))

        # Create default events for new activities
        if new_activities:
            await schedule_service.create_default_schedules(
                applet_id=applet_id,
                activity_ids=list(new_activities),
                is_activity=True,
            )
            respondents_in_applet = await UserAppletAccessCRUD(self.session).get_user_id_applet_and_role(
                applet_id=applet_id,
                role=Role.RESPONDENT,
            )

            respondents_with_indvdl_schdl: list[uuid.UUID] = []
            for respondent in respondents_in_applet:
                respondent_uuid = uuid.UUID(f"{respondent}")
                number_of_indvdl_events = await EventCRUD(self.session).count_individual_events_by_user(
                    applet_id=applet_id, user_id=respondent_uuid
                )
                if number_of_indvdl_events > 0:
                    respondents_with_indvdl_schdl.append(respondent_uuid)

            if respondents_with_indvdl_schdl:
                for respondent_uuid in respondents_with_indvdl_schdl:
                    await schedule_service.create_default_schedules(
                        applet_id=applet_id,
                        activity_ids=list(new_activities),
                        is_activity=True,
                        respondent_id=respondent_uuid,
                    )

        return activities

    async def remove_applet_activities(self, applet_id: uuid.UUID):
        await ActivityItemService(self.session).remove_applet_activity_items(applet_id)
        await ActivitiesCRUD(self.session).delete_by_applet_id(applet_id)

    async def get_single_language_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[ActivitySingleLanguageDetail]:
        schemas = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id, is_reviewable=False)
        activities = []
        for schema in schemas:
            activities.append(
                ActivitySingleLanguageDetail(
                    id=schema.id,
                    name=schema.name,
                    description=self._get_by_language(schema.description, language),
                    splash_screen=schema.splash_screen,
                    image=schema.image,
                    show_all_at_once=schema.show_all_at_once,
                    is_skippable=schema.is_skippable,
                    is_reviewable=schema.is_reviewable,
                    response_is_editable=schema.response_is_editable,
                    order=schema.order,
                    is_hidden=schema.is_hidden,
                    scores_and_reports=schema.scores_and_reports,
                    subscale_setting=schema.subscale_setting,
                    created_at=schema.created_at,
                    report_included_item_name=schema.report_included_item_name,
                    performance_task_type=schema.performance_task_type,
                    is_performance_task=schema.is_performance_task,
                    auto_assign=schema.auto_assign,
                )
            )
        return activities

    async def get_single_language_with_items_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[ActivityLanguageWithItemsMobileDetailPublic]:
        schemas = await ActivitiesCRUD(self.session).get_mobile_with_items_by_applet_id(applet_id, is_reviewable=False)

        activities = []
        activity_ids = []
        for schema in schemas:
            activity = ActivityLanguageWithItemsMobileDetailPublic(
                id=schema.id,
                name=schema.name,
                description=self._get_by_language(schema.description, language),
                splash_screen=schema.splash_screen,
                image=schema.image,
                show_all_at_once=schema.show_all_at_once,
                is_skippable=schema.is_skippable,
                is_reviewable=schema.is_reviewable,
                is_hidden=schema.is_hidden,
                response_is_editable=schema.response_is_editable,
                order=schema.order,
                scores_and_reports=schema.scores_and_reports,
                performance_task_type=schema.performance_task_type,
                is_performance_task=schema.is_performance_task,
                auto_assign=schema.auto_assign,
            )

            activities.append(activity)
            activity_ids.append(activity.id)

        activity_items_map = await ActivityItemService(self.session).get_single_language_by_activity_ids(
            activity_ids=activity_ids, language=language
        )

        for activity in activities:
            activity.items = activity_items_map.get(activity.id, [])

        return activities

    async def get_full_activities(self, applet_id: uuid.UUID) -> list[ActivityFull]:
        schemas = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id)

        activities = []
        activity_map = dict()
        for schema in schemas:
            schema.key = uuid.uuid4()
            activity = ActivityFull.from_orm(schema)
            activities.append(activity)
            activity_map[activity.id] = activity

        items = await ActivityItemService(self.session).get_items_by_activity_ids(list(activity_map.keys()))
        for item in items:
            activity_map[item.activity_id].items.append(item)

        return activities

    async def get_by_applet_id_for_duplicate(self, applet_id: uuid.UUID) -> list[ActivityDuplicate]:
        schemas = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id)
        activity_map = dict()
        activities = []
        for schema in schemas:
            activity = ActivityDuplicate(
                id=schema.id,
                key=schema.id,
                name=schema.name,
                description=schema.description,
                splash_screen=schema.splash_screen,
                image=schema.image,
                show_all_at_once=schema.show_all_at_once,
                is_skippable=schema.is_skippable,
                is_reviewable=schema.is_reviewable,
                response_is_editable=schema.response_is_editable,
                order=schema.order,
                is_hidden=schema.is_hidden,
                scores_and_reports=schema.scores_and_reports,
                subscale_setting=schema.subscale_setting,
                performance_task_type=schema.performance_task_type,
                is_performance_task=schema.is_performance_task,
                auto_assign=schema.auto_assign,
            )
            activity_map[activity.id] = activity
            activities.append(activity)
        activity_items = await ActivityItemService(self.session).get_items_by_activity_ids_for_duplicate(
            list(activity_map.keys())
        )
        for activity_item in activity_items:
            activity_map[activity_item.activity_id].items.append(activity_item)

        return activities

    async def get_single_language_by_id(
        self, activity_id: uuid.UUID, language: str
    ) -> ActivitySingleLanguageWithItemsDetail:
        schema = await ActivitiesCRUD(self.session).get_by_id(activity_id)
        activity = ActivitySingleLanguageWithItemsDetail(
            id=schema.id,
            name=schema.name,
            description=self._get_by_language(schema.description, language),
            splash_screen=schema.splash_screen,
            image=schema.image,
            show_all_at_once=schema.show_all_at_once,
            is_skippable=schema.is_skippable,
            is_reviewable=schema.is_reviewable,
            response_is_editable=schema.response_is_editable,
            order=schema.order,
            is_hidden=schema.is_hidden,
            scores_and_reports=schema.scores_and_reports,
            subscale_setting=schema.subscale_setting,
            created_at=schema.created_at,
        )
        activity.items = await ActivityItemService(self.session).get_single_language_by_activity_id(
            activity_id, language
        )
        return activity

    async def get_public_single_language_by_id(
        self, activity_id: uuid.UUID, language: str
    ) -> ActivitySingleLanguageWithItemsDetail:
        schema = await ActivitiesCRUD(self.session).get_by_id(activity_id)
        if not schema:
            raise ActivityDoeNotExist()
        applet = await AppletsCRUD(self.session).get_by_id(schema.applet_id)
        if not applet.link:
            raise ActivityAccessDeniedError()
        elif applet.require_login is True:
            raise ActivityAccessDeniedError()

        activity = ActivitySingleLanguageWithItemsDetail(
            id=schema.id,
            name=schema.name,
            description=self._get_by_language(schema.description, language),
            splash_screen=schema.splash_screen,
            image=schema.image,
            show_all_at_once=schema.show_all_at_once,
            is_skippable=schema.is_skippable,
            is_reviewable=schema.is_reviewable,
            response_is_editable=schema.response_is_editable,
            order=schema.order,
            is_hidden=schema.is_hidden,
            scores_and_reports=schema.scores_and_reports,
            subscale_setting=schema.subscale_setting,
            created_at=schema.created_at,
        )
        activity.items = await ActivityItemService(self.session).get_single_language_by_activity_id(
            activity_id, language
        )
        return activity

    @staticmethod
    def _get_by_language(values: dict, language: str):
        """
        Returns value by language key,
         if it does not exist,
         returns first existing or empty string
        """
        try:
            return values[language]
        except KeyError:
            for key, val in values.items():
                return val
            return ""

    async def update_report(self, activity_id: uuid.UUID, schema: ActivityReportConfiguration):
        crud_list: list[type[ActivitiesCRUD] | type[ActivityHistoriesCRUD]] = [
            ActivitiesCRUD,
            ActivityHistoriesCRUD,
        ]
        for crud in crud_list:
            await crud(self.session).update_by_id(activity_id, **schema.dict(by_alias=False, exclude_unset=True))

    async def get_info_by_applet_id(self, applet_id: uuid.UUID, language: str) -> list[ActivityBaseInfo]:
        schemas = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id, is_reviewable=False)
        activities = []
        activity_ids = []
        for schema in schemas:
            activity = ActivityBaseInfo(
                id=schema.id,
                name=schema.name,
                description=self._get_by_language(schema.description, language),
                image=schema.image,
                order=schema.order,
                is_hidden=schema.is_hidden,
                contains_response_types=[],
                item_count=0,
                auto_assign=schema.auto_assign,
            )

            activities.append(activity)
            activity_ids.append(activity.id)

        activity_items_map = await ActivityItemService(self.session).get_info_by_activity_ids(
            activity_ids=activity_ids, language=language
        )
        for activity in activities:
            activity.contains_response_types = list(set(activity_items_map.get(activity.id, list())))
            activity.item_count = len(activity_items_map.get(activity.id, list()))
        return activities

    async def get_activity_and_flow_basic_info_by_ids_or_auto(
        self, applet_id: uuid.UUID, ids: list[uuid.UUID], include_auto: bool, language: str
    ) -> list[ActivityOrFlowBasicInfoInternal]:
        return await ActivitiesCRUD(self.session).get_activity_and_flow_basic_info_by_ids_or_auto(
            applet_id, ids, include_auto, language
        )

    async def get_activity_and_flow_ids_by_applet_id_auto(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        activity_ids_coro = ActivitiesCRUD(self.session).get_ids_by_applet_id_auto(applet_id)
        flow_ids_coro = FlowsCRUD(self.session).get_ids_by_applet_id_auto(applet_id)

        activity_ids, flow_ids = await asyncio.gather(activity_ids_coro, flow_ids_coro)

        return activity_ids + flow_ids
