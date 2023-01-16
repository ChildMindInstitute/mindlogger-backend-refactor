from apps.activities.crud.activity_item_history import ActivityItemsHistoryCRUD
from apps.activities.db.schemas import ActivityHistorySchema
from apps.applets.domain import detailing_history
from infrastructure.database import BaseCRUD


class ActivitiesHistoryCRUD(BaseCRUD[ActivityHistorySchema]):
    schema_class = ActivityHistorySchema

    async def create_many(
        self,
        activities: list[ActivityHistorySchema],
    ):
        await self._create_many(activities)

    @staticmethod
    async def list(
        applet_id_version: str,
    ) -> tuple[
        list[detailing_history.Activity], dict[str, detailing_history.Activity]
    ]:
        return await ActivityItemsHistoryCRUD().list_by_applet_id_version(
            applet_id_version
        )
