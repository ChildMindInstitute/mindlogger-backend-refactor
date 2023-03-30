import uuid

from apps.activity_flows.crud import FlowItemsCRUD, FlowsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.activity_flows.domain.flow import FlowDetail, FlowDuplicate
from apps.activity_flows.domain.flow_create import (
    FlowCreate,
    PreparedFlowItemCreate,
)
from apps.activity_flows.domain.flow_full import FlowFull
from apps.activity_flows.domain.flow_update import (
    FlowUpdate,
    PreparedFlowItemUpdate,
)
from apps.activity_flows.service.flow_item import FlowItemService
from apps.schedule.service.schedule import ScheduleService


class FlowService:
    def __init__(self, session):
        self.session = session

    async def create(
        self,
        applet_id: uuid.UUID,
        flows_create: list[FlowCreate],
        activity_key_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> list[FlowFull]:
        schemas = list()
        prepared_flow_items = list()
        for index, flow_create in enumerate(flows_create):
            flow_id = uuid.uuid4()
            schemas.append(
                ActivityFlowSchema(
                    id=flow_id,
                    applet_id=applet_id,
                    name=flow_create.name,
                    description=flow_create.description,
                    is_single_report=flow_create.is_single_report,
                    hide_badge=flow_create.hide_badge,
                    is_hidden=flow_create.is_hidden,
                    order=index + 1,
                )
            )
            for flow_item_create in flow_create.items:
                prepared_flow_items.append(
                    PreparedFlowItemCreate(
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[
                            flow_item_create.activity_key
                        ],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemService(self.session).create(
            prepared_flow_items
        )
        flows = list()

        flow_id_map = dict()

        for flow_schema in flow_schemas:
            flow = FlowFull.from_orm(flow_schema)
            flows.append(flow)
            flow_id_map[flow.id] = flow

        for flow_item in flow_items:
            flow_id_map[flow_item.activity_flow_id].items.append(flow_item)

        # add default schedule for flows
        await ScheduleService(self.session).create_default_schedules(
            applet_id=applet_id,
            activity_ids=[flow.id for flow in flows],
            is_activity=False,
        )

        return flows

    async def update_create(
        self,
        applet_id: uuid.UUID,
        flows_update: list[FlowUpdate],
        activity_key_id_map: dict[uuid.UUID, uuid.UUID],
    ) -> list[FlowFull]:
        schemas = list()
        prepared_flow_items = list()

        all_flows = [
            flow.id
            for flow in await FlowsCRUD(self.session).get_by_applet_id(
                applet_id
            )
        ]
        # Save new flow ids
        new_flows = []
        existing_flows = []

        for index, flow_update in enumerate(flows_update):
            flow_id = flow_update.id or uuid.uuid4()

            if flow_update.id:
                existing_flows.append(flow_id)
            else:
                new_flows.append(flow_id)

            schemas.append(
                ActivityFlowSchema(
                    id=flow_id,
                    applet_id=applet_id,
                    name=flow_update.name,
                    description=flow_update.description,
                    is_single_report=flow_update.is_single_report,
                    hide_badge=flow_update.hide_badge,
                    is_hidden=flow_update.is_hidden,
                    order=index + 1,
                )
            )
            for flow_item_update in flow_update.items:
                prepared_flow_items.append(
                    PreparedFlowItemUpdate(
                        id=flow_item_update.id or uuid.uuid4(),
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[
                            flow_item_update.activity_key
                        ],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemService(self.session).create_update(
            prepared_flow_items
        )
        flows = list()

        flow_id_map = dict()

        for flow_schema in flow_schemas:
            flow = FlowFull.from_orm(flow_schema)
            flows.append(flow)
            flow_id_map[flow.id] = flow

        for flow_item in flow_items:
            flow_id_map[flow_item.activity_flow_id].items.append(flow_item)

        # Remove events for deleted flows
        deleted_flow_ids = set(all_flows) - set(existing_flows)

        if deleted_flow_ids:
            await ScheduleService(self.session).delete_by_flow_ids(
                applet_id=applet_id, flow_ids=list(deleted_flow_ids)
            )

        # Create default events for new activities
        if new_flows:
            await ScheduleService(self.session).create_default_schedules(
                applet_id=applet_id,
                activity_ids=list(new_flows),
                is_activity=False,
            )

        return flows

    async def remove_applet_flows(self, applet_id: uuid.UUID):
        await FlowItemService(self.session).remove_applet_flow_items(applet_id)
        await FlowsCRUD(self.session).delete_by_applet_id(applet_id)

    async def get_single_language_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[FlowDetail]:
        schemas = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_ids = []
        flow_map = dict()
        flows = []
        for schema in schemas:
            flow_ids.append(schema.id)

            flow = FlowDetail(
                id=schema.id,
                name=schema.name,
                description=self._get_by_language(
                    schema.description, language
                ),
                is_single_report=schema.is_single_report,
                hide_badge=schema.hide_badge,
                order=schema.order,
                is_hidden=schema.is_hidden,
            )
            flow_map[flow.id] = flow
            flows.append(flow)
        schemas = await FlowItemsCRUD(self.session).get_by_applet_id(applet_id)
        for schema in schemas:
            flow_map[schema.activity_flow_id].activity_ids.append(
                schema.activity_id
            )

        return flows

    async def get_by_applet_id(
        self, applet_id: uuid.UUID
    ) -> list[FlowDuplicate]:
        schemas = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_ids = []
        flow_map = dict()
        flows = []
        for schema in schemas:
            flow_ids.append(schema.id)

            flow = FlowDuplicate(
                id=schema.id,
                name=schema.name,
                description=schema.description,
                is_single_report=schema.is_single_report,
                hide_badge=schema.hide_badge,
                order=schema.order,
                is_hidden=schema.is_hidden,
            )
            flow_map[flow.id] = flow
            flows.append(flow)
        schemas = await FlowItemsCRUD(self.session).get_by_applet_id(applet_id)
        for schema in schemas:
            flow_map[schema.activity_flow_id].activity_ids.append(
                schema.activity_id
            )

        return flows

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
