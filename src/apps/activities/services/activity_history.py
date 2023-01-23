from apps.activities.crud import ActivityHistoriesCRUD
from apps.activities.domain import ActivityHistory, ActivityHistoryChange

__all__ = ["ActivityHistoryService"]

from apps.shared.changes_generator import ChangeTextGenerator
from apps.shared.version import get_prev_version


class ActivityHistoryService:
    def __init__(self, applet_id: int, version: str):
        self._applet_id = applet_id
        self._version = version
        self._applet_id_version = f"{applet_id}_{version}"

    async def get_changes(self):
        prev_version = get_prev_version(self._version)
        old_id_version = f"{self._applet_id}_{prev_version}"
        return await self._get_activity_changes(old_id_version)

    async def _get_activity_changes(
        self, old_applet_id_version: str
    ) -> list[ActivityHistoryChange]:
        generator = ChangeTextGenerator()
        activity_changes: list[ActivityHistoryChange] = []
        activity_schemas = await ActivityHistoriesCRUD().retrieve_by_applet_versions_ordered_by_id(
            [self._applet_id_version, old_applet_id_version]
        )
        activities = [
            ActivityHistory.from_orm(schema) for schema in activity_schemas
        ]

        activity_groups = self._group_and_sort_activities(activities)
        for _, (prev_activity, new_activity) in activity_groups.items():
            if not prev_activity:
                activity_changes.append(
                    ActivityHistoryChange(
                        name=generator.added_text(
                            f"activity by name {new_activity.name}"
                        )
                    )
                )
            elif not new_activity:
                activity_changes.append(
                    ActivityHistoryChange(
                        name=generator.removed_text(
                            f"activity by name {prev_activity.name}"
                        )
                    )
                )
            else:
                change = ActivityHistoryChange()
                has_changes = False
                if prev_activity.name != new_activity.name:
                    has_changes = True
                    if generator.is_considered_empty(new_activity.name):
                        change.name = generator.cleared_text("name")
                    else:
                        change.name = generator.filled_text(
                            "name", new_activity.name
                        )
                if prev_activity.description != new_activity.description:
                    has_changes = True
                    change.description = generator.updated_text("description")
                if prev_activity.splash_screen != new_activity.splash_screen:
                    has_changes = True
                    change.splash_screen = generator.updated_text(
                        "splash screen"
                    )
                if prev_activity.image != new_activity.image:
                    has_changes = True
                    change.image = generator.updated_text("image")
                if (
                    prev_activity.show_all_at_once
                    != new_activity.show_all_at_once
                ):
                    has_changes = True
                    change.show_all_at_once = generator.changed_text(
                        prev_activity.show_all_at_once,
                        new_activity.show_all_at_once,
                    )
                if prev_activity.is_skippable != new_activity.is_skippable:
                    has_changes = True
                    change.is_skippable = generator.changed_text(
                        prev_activity.is_skippable, new_activity.is_skippable
                    )
                if prev_activity.is_reviewable != new_activity.is_reviewable:
                    has_changes = True
                    change.is_reviewable = generator.changed_text(
                        prev_activity.is_reviewable, new_activity.is_reviewable
                    )
                if (
                    prev_activity.response_is_editable
                    != new_activity.response_is_editable
                ):
                    has_changes = True
                    change.response_is_editable = generator.changed_text(
                        prev_activity.response_is_editable,
                        new_activity.response_is_editable,
                    )
                if prev_activity.ordering != new_activity.ordering:
                    has_changes = True
                    change.ordering = generator.changed_text(
                        prev_activity.ordering, new_activity.ordering
                    )
                if has_changes:
                    activity_changes.append(change)
        return activity_changes

    def _group_and_sort_activities(
        self, activities: list[ActivityHistory]
    ) -> dict[int, tuple[ActivityHistory, ActivityHistory]]:
        groups_map = dict()
        for activity in activities:
            group = list(groups_map.get(activity.id, ()))
            if len(group) == 0:
                if self._version in activity.id_version.split("_"):
                    group = [None, activity]
                else:
                    group = [activity, None]
            else:
                if self._version in activity.id_version.split("_"):
                    group[1] = activity
                else:
                    group[0] = activity
            groups_map[activity.id] = tuple(group)

        return groups_map
