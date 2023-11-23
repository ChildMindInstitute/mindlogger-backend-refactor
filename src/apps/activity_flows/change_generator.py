import uuid

from apps.activity_flows.domain.flow_full import (
    FlowHistoryFull,
    FlowItemHistoryFull,
)
from apps.activity_flows.domain.flow_history import (
    ActivityFlowItemHistoryChange,
)
from apps.shared.changes_generator import BaseChangeGenerator
from apps.shared.domain import to_camelcase

NOT_TRACKED_FIELDS = (
    "id",
    "created_at",
    "id_version",
    "activity_flow_id",
    "activity_id",
    "applet_id",
    "items",
)


class ActivityFlowChangeGenerator(BaseChangeGenerator):
    def generate_flow_insert(self, flow: FlowHistoryFull) -> list[str]:
        changes = list()
        for field, value in flow.dict().items():
            if field in NOT_TRACKED_FIELDS:
                continue
            elif isinstance(value, bool):
                changes.append(
                    self._change_text_generator.set_bool(
                        f"Activity Flow {to_camelcase(field)}",
                        "enabled" if value else "disabled",
                    ),
                )
            elif field == "description":
                changes.append(
                    self._change_text_generator.set_dict(
                        f"Activity Flow {to_camelcase(field)}", value
                    )
                )
            elif value:
                changes.append(
                    self._change_text_generator.set_text(
                        f"Activity Flow {to_camelcase(field)}", value
                    ),
                )
        return changes

    def generate_flow_update(
        self, new_flow: FlowHistoryFull, old_flow: FlowHistoryFull
    ) -> list[str]:
        changes = list()
        for field, value in new_flow.dict().items():
            old_value = getattr(old_flow, field, None)
            if field in NOT_TRACKED_FIELDS:
                continue
            # Possible we can track bool not bool in generator.
            elif isinstance(value, bool):
                if value != old_value:
                    changes.append(
                        self._change_text_generator.set_bool(
                            f"Activity Flow {to_camelcase(field)}",
                            "enabled" if value else "disabled",
                        ),
                    )
            elif value != old_value:
                if field == "description":
                    desc_change = f"Activity Flow {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, value)}."  # noqa: E501
                    changes.append(desc_change)
                else:
                    changes.append(
                        self._change_text_generator.changed_text(
                            f"Activity Flow {to_camelcase(field)}", value
                        )
                    )
        return changes

    def generate_flow_items_insert(
        self, flow_items: list[FlowItemHistoryFull]
    ) -> list[ActivityFlowItemHistoryChange]:
        change_items = []
        for item in flow_items:
            change = ActivityFlowItemHistoryChange(
                name=self._change_text_generator.added_text(
                    f"Activity {item.name}"
                )
            )
            changes = []
            for field, value in item.dict().items():
                if field == "order":
                    changes.append(
                        self._change_text_generator.set_text(
                            f"Activity {to_camelcase(field)}", value
                        )
                    )

            change.changes = changes
            change_items.append(change)

        return change_items

    def generate_flow_items_update(
        self,
        item_groups: dict[
            uuid.UUID,
            tuple[FlowItemHistoryFull | None, FlowItemHistoryFull | None],
        ],
    ) -> list[ActivityFlowItemHistoryChange]:
        change_items: list[ActivityFlowItemHistoryChange] = []

        for _, (prev_item, new_item) in item_groups.items():
            if not prev_item and new_item:
                change_items.extend(
                    self.generate_flow_items_insert([new_item])
                )
            elif not new_item and prev_item:
                change_items.append(
                    ActivityFlowItemHistoryChange(
                        name=self._change_text_generator.removed_text(
                            f"Activity {prev_item.name}"
                        )
                    )
                )

        return change_items
