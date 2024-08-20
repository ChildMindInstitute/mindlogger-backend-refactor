import uuid

from apps.activity_flows.crud import FlowItemsCRUD, FlowsCRUD, FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.activity_flows.domain.flow import Flow, FlowBaseInfo, FlowDuplicate, FlowSingleLanguageDetail
from apps.activity_flows.domain.flow_create import FlowCreate, PreparedFlowItemCreate
from apps.activity_flows.domain.flow_full import FlowFull
from apps.activity_flows.domain.flow_update import ActivityFlowReportConfiguration, FlowUpdate, PreparedFlowItemUpdate
from apps.activity_flows.service.flow_item import FlowItemService
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain.applet_history import Version
from apps.schedule.crud.events import EventCRUD, FlowEventsCRUD
from apps.schedule.service.schedule import ScheduleService
from apps.workspaces.domain.constants import Role


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
                    report_included_activity_name=flow_create.report_included_activity_name,  # noqa: E501
                    report_included_item_name=flow_create.report_included_item_name,  # noqa: E501
                    extra_fields=flow_create.extra_fields,
                    order=index + 1,
                    auto_assign=flow_create.auto_assign,
                )
            )
            for flow_item_create in flow_create.items:
                prepared_flow_items.append(
                    PreparedFlowItemCreate(
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[flow_item_create.activity_key],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemService(self.session).create(prepared_flow_items)
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

        all_flows = [flow.flow_id for flow in await FlowEventsCRUD(self.session).get_by_applet_id(applet_id)]

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
                    report_included_activity_name=(flow_update.report_included_activity_name),
                    report_included_item_name=(flow_update.report_included_item_name),
                )
            )
            for flow_item_update in flow_update.items:
                prepared_flow_items.append(
                    PreparedFlowItemUpdate(
                        id=flow_item_update.id or uuid.uuid4(),
                        activity_flow_id=flow_id,
                        activity_id=activity_key_id_map[flow_item_update.activity_key],
                    )
                )
        flow_schemas = await FlowsCRUD(self.session).create_many(schemas)
        flow_items = await FlowItemService(self.session).create_update(prepared_flow_items)
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
            await ScheduleService(self.session).delete_by_flow_ids(applet_id=applet_id, flow_ids=list(deleted_flow_ids))

        # Create default events for new activities
        if new_flows:
            await ScheduleService(self.session).create_default_schedules(
                applet_id=applet_id,
                activity_ids=list(new_flows),
                is_activity=False,
            )
            respondents_in_applet = await UserAppletAccessCRUD(self.session).get_user_id_applet_and_role(
                applet_id=applet_id,
                role=Role.RESPONDENT,
            )

            respondents_with_indvdl_schdl = []
            for respondent in respondents_in_applet:
                respondent_uuid = uuid.UUID(f"{respondent}")
                number_of_indvdl_events = await EventCRUD(self.session).count_individual_events_by_user(
                    applet_id=applet_id, user_id=respondent_uuid
                )
                if number_of_indvdl_events > 0:
                    respondents_with_indvdl_schdl.append(respondent_uuid)

            if respondents_with_indvdl_schdl:
                for respondent_uuid in respondents_with_indvdl_schdl:
                    await ScheduleService(self.session).create_default_schedules(
                        applet_id=applet_id,
                        activity_ids=list(new_flows),
                        is_activity=False,
                        respondent_id=respondent_uuid,
                    )

        return flows

    async def remove_applet_flows(self, applet_id: uuid.UUID):
        await FlowItemService(self.session).remove_applet_flow_items(applet_id)
        await FlowsCRUD(self.session).delete_by_applet_id(applet_id)

    async def get_single_language_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[FlowSingleLanguageDetail]:
        schemas = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_ids = []
        flow_map = dict()
        flows = []
        for schema in schemas:
            flow_ids.append(schema.id)

            flow = FlowSingleLanguageDetail(
                id=schema.id,
                name=schema.name,
                description=self._get_by_language(schema.description, language),
                is_single_report=schema.is_single_report,
                hide_badge=schema.hide_badge,
                order=schema.order,
                is_hidden=schema.is_hidden,
                created_at=schema.created_at,
                report_included_activity_name=schema.report_included_activity_name,  # noqa: E501
                report_included_item_name=schema.report_included_item_name,
            )
            flow_map[flow.id] = flow
            flows.append(flow)
        schemas = await FlowItemsCRUD(self.session).get_by_applet_id(applet_id)
        for schema in schemas:
            flow_map[schema.activity_flow_id].activity_ids.append(schema.activity_id)

        return flows

    async def get_by_applet_id_duplicate(self, applet_id: uuid.UUID) -> list[FlowDuplicate]:
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
            flow_map[schema.activity_flow_id].activity_ids.append(schema.activity_id)

        return flows

    async def get_full_flows(self, applet_id: uuid.UUID) -> list[FlowFull]:
        schemas = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_map = dict()
        flows = []
        for schema in schemas:
            flow = FlowFull.from_orm(schema)
            flow_map[flow.id] = flow
            flows.append(flow)
        items = await FlowItemService(self.session).get_by_flow_ids(list(flow_map.keys()))
        for item in items:
            flow_map[item.activity_flow_id].items.append(item)

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

    async def update_report_config(self, flow_id: uuid.UUID, schema: ActivityFlowReportConfiguration):
        await FlowsCRUD(self.session).update_by_id(flow_id, **schema.dict(by_alias=False))

    async def get_by_id(self, flow_id: uuid.UUID) -> Flow | None:
        return await FlowsCRUD(self.session).get_by_id(flow_id)

    async def get_info_by_applet_id(self, applet_id: uuid.UUID, language: str) -> list[FlowBaseInfo]:
        schemas = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_ids = []
        flow_map = dict()
        flows = []
        for schema in schemas:
            flow_ids.append(schema.id)

            flow = FlowBaseInfo(
                id=schema.id,
                name=schema.name,
                description=self._get_by_language(schema.description, language),
                hide_badge=schema.hide_badge,
                order=schema.order,
                is_hidden=schema.is_hidden,
                auto_assign=schema.auto_assign,
            )
            flow_map[flow.id] = flow
            flows.append(flow)
        schemas = await FlowItemsCRUD(self.session).get_by_applet_id(applet_id)
        for schema in schemas:
            flow_map[schema.activity_flow_id].activity_ids.append(schema.activity_id)
        return flows

    async def get_versions(self, applet_id: uuid.UUID, flow_id: uuid.UUID) -> list[Version]:
        return await FlowsHistoryCRUD(self.session).get_versions_data(applet_id, flow_id)
