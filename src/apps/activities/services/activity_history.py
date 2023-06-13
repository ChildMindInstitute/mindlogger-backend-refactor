import uuid
from typing import Optional

from apps.activities.crud import ActivityHistoriesCRUD
from apps.activities.db.schemas import ActivityHistorySchema
from apps.activities.domain import ActivityHistory, ActivityHistoryChange

__all__ = ["ActivityHistoryService"]

from apps.activities.domain.activity_full import ActivityFull
from apps.activities.errors import InvalidVersionError
from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.shared.changes_generator import ChangeTextGenerator
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
        activity_changes: list[ActivityHistoryChange] = []
        activity_schemas = await ActivityHistoriesCRUD(
            self.session
        ).retrieve_by_applet_ids(
            [self._applet_id_version, old_applet_id_version]
        )
        activities = [
            ActivityHistory.from_orm(schema) for schema in activity_schemas
        ]

        activity_groups = self._group_and_sort_activities(activities)
        for _, (prev_activity, new_activity) in activity_groups.items():
            if not prev_activity and new_activity:
                activity_changes.append(
                    ActivityHistoryChange(
                        name=changes_generator.added_text(
                            f"activity by name {new_activity.name}"
                        )
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
                change = ActivityHistoryChange()
                has_changes = False
                if prev_activity.name != new_activity.name:
                    has_changes = True
                    if changes_generator.is_considered_empty(
                        new_activity.name
                    ):
                        change.name = changes_generator.cleared_text("name")
                    else:
                        change.name = changes_generator.filled_text(
                            "name", new_activity.name
                        )
                if prev_activity.description != new_activity.description:
                    has_changes = True
                    change.description = changes_generator.updated_text(
                        "description"
                    )
                if prev_activity.splash_screen != new_activity.splash_screen:
                    has_changes = True
                    change.splash_screen = changes_generator.updated_text(
                        "splash screen"
                    )
                if prev_activity.image != new_activity.image:
                    has_changes = True
                    change.image = changes_generator.updated_text("image")
                if (
                    prev_activity.show_all_at_once
                    != new_activity.show_all_at_once
                ):
                    has_changes = True
                    change.show_all_at_once = changes_generator.changed_text(
                        prev_activity.show_all_at_once,
                        new_activity.show_all_at_once,
                    )
                if prev_activity.is_skippable != new_activity.is_skippable:
                    has_changes = True
                    change.is_skippable = changes_generator.changed_text(
                        prev_activity.is_skippable, new_activity.is_skippable
                    )
                if prev_activity.is_reviewable != new_activity.is_reviewable:
                    has_changes = True
                    change.is_reviewable = changes_generator.changed_text(
                        prev_activity.is_reviewable, new_activity.is_reviewable
                    )
                if (
                    prev_activity.response_is_editable
                    != new_activity.response_is_editable
                ):
                    has_changes = True
                    change.response_is_editable = (
                        changes_generator.changed_text(
                            prev_activity.response_is_editable,
                            new_activity.response_is_editable,
                        )
                    )
                if prev_activity.order != new_activity.order:
                    has_changes = True
                    change.order = changes_generator.changed_text(
                        prev_activity.order, new_activity.order
                    )
                if has_changes:
                    activity_changes.append(change)
        return activity_changes

    def _group_and_sort_activities(
        self, activities: list[ActivityHistory]
    ) -> dict[
        uuid.UUID, tuple[Optional[ActivityHistory], Optional[ActivityHistory]]
    ]:
        groups_map: dict[
            uuid.UUID, tuple[ActivityHistory | None, ActivityHistory | None]
        ] = dict()
        for activity in activities:
            group = groups_map.get(activity.id)
            if not group:
                if self._version in activity.id_version.split("_"):
                    group = (None, activity)
                else:
                    group = (activity, None)
            elif group:
                if self._version in activity.id_version.split("_"):
                    group = (group[0], activity)
                else:
                    group = (activity, group[1])
            groups_map[activity.id] = group

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
