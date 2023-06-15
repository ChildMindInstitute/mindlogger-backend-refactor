import uuid
from typing import Optional

from apps.activities.crud import ActivityHistoriesCRUD
from apps.activities.db.schemas import ActivityHistorySchema
from apps.activities.domain import (
    ActivityHistory,
    ActivityHistoryChange,
    ActivityHistoryFull,
)
from apps.activities.domain.activity_item_history import ActivityItemHistory

__all__ = ["ActivityHistoryService"]

from apps.activities.domain.activity_full import ActivityFull
from apps.activities.errors import InvalidVersionError
from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.shared.changes_generator import ChangeGenerator, ChangeTextGenerator
from apps.shared.version import get_prev_version


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
                    is_assessment=activity.is_assessment,
                    is_hidden=activity.is_hidden,
                    scores_and_reports=activity.scores_and_reports.dict()
                    if activity.scores_and_reports
                    else None,
                    subscale_setting=activity.subscale_setting.dict()
                    if activity.subscale_setting
                    else None,
                )
            )

        await ActivityHistoriesCRUD(self.session).create_many(schemas)
        await ActivityItemHistoryService(
            self.session, self._applet_id, self._version
        ).add(activity_items)

    async def get_changes(self):
        try:
            prev_version = get_prev_version(self._version)
        except ValueError:
            raise InvalidVersionError()
        old_id_version = f"{self._applet_id}_{prev_version}"
        return await self._get_activity_changes(old_id_version)

    async def _get_activity_changes(
        self, old_applet_id_version: str
    ) -> list[ActivityHistoryChange]:
        changes_generator = ChangeTextGenerator()
        change_activity_generator = ChangeGenerator()

        activity_changes: list[ActivityHistoryChange] = []
        activity_schemas = await ActivityHistoriesCRUD(
            self.session
        ).retrieve_by_applet_ids(
            [self._applet_id_version, old_applet_id_version]
        )
        activities = [
            ActivityHistoryFull.from_orm(schema) for schema in activity_schemas
        ]
        for activity in activities:
            activity.items = await ActivityItemHistoryService(
                self.session, self._applet_id, self._version
            ).get_by_activity_id_versions([activity.id_version])

        activity_groups = self._group_and_sort_activities_or_items(activities)
        for _, (prev_activity, new_activity) in activity_groups.items():
            if not prev_activity and new_activity:
                activity_changes.append(
                    ActivityHistoryChange(
                        name=changes_generator.added_text(
                            f"activity by name {new_activity.name}"
                        ),
                        changes=change_activity_generator.generate_activity_insert(  # noqa: E501
                            new_activity
                        ),
                        items=change_activity_generator.generate_activity_items_insert(  # noqa: E501
                            getattr(new_activity, "items", [])
                        ),
                    )
                )
            elif not new_activity and prev_activity:
                activity_changes.append(
                    ActivityHistoryChange(
                        name=changes_generator.removed_text(
                            f"activity by name {prev_activity.name}"
                        )
                    )
                )
            elif new_activity and prev_activity:
                has_changes = False
                (
                    changes,
                    has_changes,
                ) = change_activity_generator.generate_activity_update(
                    new_activity, prev_activity
                )
                changes_items = []
                (
                    changes_items,
                    has_changes,
                ) = change_activity_generator.generate_activity_items_update(
                    self._group_and_sort_activities_or_items(
                        getattr(new_activity, "items", [])
                        + getattr(prev_activity, "items", [])
                    ),
                )

                if has_changes:
                    activity_changes.append(
                        ActivityHistoryChange(
                            name=changes_generator.updated_text(
                                f"Activity {new_activity.name}"
                            ),
                            changes=changes,
                            items=changes_items,
                        )
                    )
        return activity_changes

    def _group_and_sort_activities_or_items(
        self, items: list[ActivityHistoryFull] | list[ActivityItemHistory]
    ) -> dict[
        uuid.UUID,
        tuple[Optional[ActivityHistoryFull], Optional[ActivityHistoryFull]]
        | tuple[Optional[ActivityItemHistory], Optional[ActivityItemHistory]],
    ]:
        groups_map: dict = dict()
        for item in items:
            group = groups_map.get(item.id)
            if not group:
                if self._version in item.id_version.split("_"):
                    group = (None, item)
                else:
                    group = (item, None)
            elif group:
                if self._version in item.id_version.split("_"):
                    group = (group[0], item)
                else:
                    group = (item, group[1])
            groups_map[item.id] = group

        return groups_map

    async def get_by_history_ids(
        self, activity_ids: list[str]
    ) -> list[ActivityHistory]:
        schemas = await ActivityHistoriesCRUD(self.session).get_by_ids(
            activity_ids
        )
        return [ActivityHistory.from_orm(schema) for schema in schemas]

    async def activities_list(self) -> list[ActivityHistory]:
        schemas = await ActivityHistoriesCRUD(
            self.session
        ).retrieve_activities_by_applet_version(self._applet_id_version)
        return [ActivityHistory.from_orm(schema) for schema in schemas]

    async def get_by_id(self, activity_id: uuid.UUID) -> ActivityHistory:
        schema = await ActivityHistoriesCRUD(self.session).get_by_id(
            f"{activity_id}_{self._version}"
        )
        return ActivityHistory.from_orm(schema)
