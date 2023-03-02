import uuid

from apps.activity_flows.crud import FlowItemsCRUD, FlowsCRUD
from apps.activity_flows.domain.flow import FlowDetail


class FlowService:
    async def get_single_language_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[FlowDetail]:
        schemas = await FlowsCRUD().get_by_applet_id(applet_id)
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
                ordering=schema.ordering,
            )
            flow_map[flow.id] = flow
            flows.append(flow)
        schemas = await FlowItemsCRUD().get_by_applet_id(applet_id)
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
