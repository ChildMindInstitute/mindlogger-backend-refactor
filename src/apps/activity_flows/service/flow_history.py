import uuid

from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.activity_flows.domain.flow_full import (
    FlowFull,
    FlowHistoryFull,
    FlowItemHistoryFull,
)
from apps.activity_flows.domain.flow_history import ActivityFlowHistoryChange
from apps.activity_flows.service.flow_change import (
    ActivityFlowChangeService,
    ActivityFlowItemChangeService,
)
from apps.activity_flows.service.flow_item_history import (
    FlowItemHistoryService,
)
from apps.shared.changes_generator import ChangeTextGenerator


class FlowHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version
        self.applet_id_version = f"{applet_id}_{version}"
        self.session = session

    async def add(self, flows: list[FlowFull]):
        flow_items = []
        schemas = []

        for flow in flows:
            flow_items += flow.items
            schemas.append(
                ActivityFlowHistoriesSchema(
                    id_version=f"{flow.id}_{self.version}",
                    id=flow.id,
                    applet_id=self.applet_id_version,
                    name=flow.name,
                    description=flow.description,
                    is_single_report=flow.is_single_report,
                    hide_badge=flow.hide_badge,
                    order=flow.order,
                    report_included_activity_name=flow.report_included_activity_name,  # noqa: E501
                    report_included_item_name=flow.report_included_item_name,
                )
            )

        await FlowsHistoryCRUD(self.session).create_many(schemas)
        await FlowItemHistoryService(
            self.session, self.applet_id, self.version
        ).add(flow_items)

    async def get_full(self) -> list[FlowHistoryFull]:
        schemas = await FlowsHistoryCRUD(self.session).get_by_applet_id(
            self.applet_id_version
        )
        flows = list()
        flow_map: dict[str, FlowHistoryFull] = dict()
        flow_ids = list()

        for schema in schemas:
            flow: FlowHistoryFull = FlowHistoryFull.from_orm(schema)
            flows.append(flow)
            flow_ids.append(flow.id)
            flow_map[flow.id_version] = flow

        items = await FlowItemHistoryService(
            self.session, self.applet_id, self.version
        ).get_by_flow_ids(flow_ids)

        for item in items:
            flow_map[item.activity_flow_id].items.append(item)

        return flows

    async def get_changes(
        self, prev_version: str
    ) -> list[ActivityFlowHistoryChange]:
        old_id_version = f"{self.applet_id}_{prev_version}"
        return await self._get_changes(old_id_version)

    async def _get_changes(
        self, old_id_version: str
    ) -> list[ActivityFlowHistoryChange]:
        changes_generator = ChangeTextGenerator()
        flow_change_service = ActivityFlowChangeService()
        flow_item_change_service = ActivityFlowItemChangeService()
        flow_changes: list[ActivityFlowHistoryChange] = []
        flow_schemas = await FlowsHistoryCRUD(
            self.session
        ).retrieve_by_applet_ids([self.applet_id_version, old_id_version])
        flows = []
        for schema in flow_schemas:
            flow = FlowHistoryFull.from_orm(schema)
            flow.items = await FlowItemHistoryService(
                self.session, self.applet_id, self.version
            ).get_by_flow_id_versions([flow.id_version])
            flows.append(flow)
        flow_groups = self._group_and_sort_flows_or_items(flows)
        for _, (prev, new) in flow_groups.items():
            if not prev and new:
                flow_changes.append(
                    ActivityFlowHistoryChange(
                        name=changes_generator.added_text(
                            f"Activity Flow by name {new.name}"
                        ),
                        changes=flow_change_service.generate_flow_insert(
                            new  # type: ignore
                        ),
                        items=flow_item_change_service.generate_flow_items_insert(  # noqa E501
                            getattr(new, "items", [])
                        ),
                    )
                )
            elif not new and prev:
                flow_changes.append(
                    ActivityFlowHistoryChange(
                        name=changes_generator.removed_text(
                            f"Activity Flow by name {prev.name}"
                        )
                    )
                )
            elif new and prev:
                changes = flow_change_service.generate_flow_update(
                    new,  # type: ignore
                    prev,  # type: ignore
                )
                changes_items = flow_item_change_service.generate_flow_items_update(  # noqa: E501
                    self._group_and_sort_flows_or_items(
                        getattr(new, "items", []) + getattr(prev, "items", [])
                    ),  # type: ignore
                )

                if changes or changes_items:
                    flow_changes.append(
                        ActivityFlowHistoryChange(
                            name=changes_generator.updated_text(
                                f"Activity Flow {new.name}"
                            ),
                            changes=changes,
                            items=changes_items,
                        )
                    )
        return flow_changes

    def _group_and_sort_flows_or_items(
        self, items: list[FlowHistoryFull] | list[FlowItemHistoryFull]
    ) -> dict[
        uuid.UUID,
        tuple[FlowHistoryFull | None, FlowHistoryFull | None]
        | tuple[FlowItemHistoryFull | None, FlowItemHistoryFull | None],
    ]:
        groups_map: dict = dict()
        for item in items:
            group = groups_map.get(item.id)
            if not group:
                if self.version in item.id_version.split("_"):
                    group = (None, item)
                else:
                    group = (item, None)
            elif group:
                if self.version in item.id_version.split("_"):
                    group = (group[0], item)
                else:
                    group = (item, group[1])
            groups_map[item.id] = group

        return groups_map
