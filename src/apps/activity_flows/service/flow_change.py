import uuid

from apps.activity_flows.domain.flow_full import FlowHistoryFull, FlowItemHistoryFull
from apps.activity_flows.domain.flow_history import ActivityFlowItemHistoryChange
from apps.shared.changes_generator import BaseChangeGenerator


class ActivityFlowChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "name": "Activity Flow Name",
        "description": "Activity Flow Description",
        "is_single_report": "Combine reports into a single file",
        "hide_badge": "Hide Badge",
        "is_hidden": "Activity Flow Visibility",
    }

    def generate_flow_insert(self, flow: FlowHistoryFull) -> list[str]:
        changes: list[str] = list()
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            value = getattr(flow, field_name)
            if isinstance(value, bool):
                self._populate_bool_changes(verbose_name, value, changes)
            elif value:
                changes.append(
                    self._change_text_generator.changed_text(verbose_name, value, is_initial=True),
                )
        return changes

    def generate_flow_update(self, new_flow: FlowHistoryFull, old_flow: FlowHistoryFull) -> list[str]:
        changes: list[str] = list()
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            new_value = getattr(new_flow, field_name)
            old_value = getattr(old_flow, field_name)
            if isinstance(new_value, bool):
                if new_value != old_value:
                    self._populate_bool_changes(verbose_name, new_value, changes)
            elif new_value != old_value:
                changes.append(
                    self._change_text_generator.changed_text(verbose_name, new_value),
                )
        return changes


class ActivityFlowItemChangeService(BaseChangeGenerator):
    def generate_flow_items_insert(self, flow_items: list[FlowItemHistoryFull]) -> list[ActivityFlowItemHistoryChange]:
        change_items = []
        for item in flow_items:
            change = ActivityFlowItemHistoryChange(name=self._change_text_generator.added_text(f"Activity {item.name}"))
            changes: list[str] = []
            for field, value in item:
                if field == "order":
                    verbose_name = "Activity Order"
                    changes.append(self._change_text_generator.set_text(verbose_name, value))

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
                change_items.extend(self.generate_flow_items_insert([new_item]))
            elif not new_item and prev_item:
                change_items.append(
                    ActivityFlowItemHistoryChange(
                        name=self._change_text_generator.removed_text(f"Activity {prev_item.name}")
                    )
                )
            elif prev_item and new_item:
                changes = self._generate_flow_item_update(prev_item, new_item)
                if changes:
                    change_items.append(
                        ActivityFlowItemHistoryChange(
                            name=self._change_text_generator.updated_text(f"Activity {new_item.name}"),
                            changes=changes,
                        )
                    )

        return change_items

    def _generate_flow_item_update(self, prev_item: FlowItemHistoryFull, new_item: FlowItemHistoryFull) -> list[str]:
        changes: list[str] = []
        if prev_item.order != new_item.order:
            changes.append(
                self._change_text_generator.changed_text(
                    "Activity Order",
                    new_item.order,
                ),
            )
        return changes
