from apps.activity_flows.crud.flow_item_history import FlowItemsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.applets.domain import detailing_history
from infrastructure.database import BaseCRUD


class FlowsHistoryCRUD(BaseCRUD[ActivityFlowHistoriesSchema]):
    schema_class = ActivityFlowHistoriesSchema

    async def create_many(
        self,
        flows: list[ActivityFlowHistoriesSchema],
    ):
        await self._create_many(flows)

    @staticmethod
    async def list(
        applet_id_version: str,
        activities_map: dict[str, detailing_history.Activity],
    ) -> list[detailing_history.ActivityFlow]:
        return await FlowItemsHistoryCRUD().list_by_applet_id_version(
            applet_id_version, activities_map
        )
