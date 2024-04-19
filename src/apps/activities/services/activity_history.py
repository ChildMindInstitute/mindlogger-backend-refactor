import uuid

from apps.activities.crud import ActivityHistoriesCRUD
from apps.activities.db.schemas import ActivityHistorySchema
from apps.activities.domain import ActivityHistory, ActivityHistoryChange, ActivityHistoryFull
from apps.activities.domain.activity_full import ActivityFull, ActivityItemHistoryFull
from apps.activities.services.activity_change import ActivityChangeService
from apps.activities.services.activity_item_history import ActivityItemHistoryService

__all__ = ["ActivityHistoryService"]


class ActivityHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self._applet_id = applet_id
        self._version = version
        self._applet_id_version = f"{applet_id}_{version}"
        self.session = session

    async def add(self, activities: list[ActivityFull]):
        activity_items = []
        schemas = []

        for activity in activities:
            activity_items += activity.items
            schemas.append(
                ActivityHistorySchema(
                    id=activity.id,
                    id_version=f"{activity.id}_{self._version}",
                    applet_id=self._applet_id_version,
                    name=activity.name,
                    description=activity.description,
                    splash_screen=activity.splash_screen,
                    image=activity.image,
                    show_all_at_once=activity.show_all_at_once,
                    is_skippable=activity.is_skippable,
                    is_reviewable=activity.is_reviewable,
                    response_is_editable=activity.response_is_editable,
                    order=activity.order,
                    is_hidden=activity.is_hidden,
                    scores_and_reports=activity.scores_and_reports.dict() if activity.scores_and_reports else None,
                    subscale_setting=activity.subscale_setting.dict() if activity.subscale_setting else None,
                    report_included_item_name=activity.report_included_item_name,  # noqa: E501
                    performance_task_type=activity.performance_task_type,
                )
            )

        await ActivityHistoriesCRUD(self.session).create_many(schemas)
        await ActivityItemHistoryService(self.session, self._applet_id, self._version).add(activity_items)

    async def get_changes(self, prev_version: str) -> list[ActivityHistoryChange]:
        old_applet_id_version = f"{self._applet_id}_{prev_version}"

        activity_schemas = await ActivityHistoriesCRUD(self.session).retrieve_by_applet_ids(
            [self._applet_id_version, old_applet_id_version]
        )
        activities = [ActivityHistoryFull.from_orm(schema) for schema in activity_schemas]
        activities_id_versions = [activity.id_version for activity in activities]
        activity_items = await ActivityItemHistoryService(
            self.session, self._applet_id, self._version
        ).get_by_activity_id_versions(activities_id_versions)
        activity_items_map: dict[str, list[ActivityItemHistoryFull]] = dict()
        for item in activity_items:
            activity_items_map.setdefault(f"{item.activity_id}", []).append(item)

        for activity in activities:
            activity.items = activity_items_map.get(activity.id_version, [])
        service = ActivityChangeService(prev_version, self._version)
        return service.get_changes(activities)

    async def activities_list(self) -> list[ActivityHistory]:
        schemas = await ActivityHistoriesCRUD(self.session).retrieve_activities_by_applet_version(
            self._applet_id_version
        )
        return [ActivityHistory.from_orm(schema) for schema in schemas]

    async def get_full(self, non_performance=False) -> list[ActivityHistoryFull]:
        schemas = await ActivityHistoriesCRUD(self.session).get_by_applet_id_version(
            self._applet_id_version, non_performance
        )
        activities = []
        activity_ids = []
        activity_map = dict()
        for schema in schemas:
            schema.key = uuid.uuid4()
            activity: ActivityHistoryFull = ActivityHistoryFull.from_orm(schema)
            activities.append(activity)
            activity_map[activity.id_version] = activity
            activity_ids.append(activity.id)

        items = await ActivityItemHistoryService(self.session, self._applet_id, self._version).get_by_activity_ids(
            activity_ids
        )

        for item in items:
            activity_map[item.activity_id].items.append(item)

        return activities
