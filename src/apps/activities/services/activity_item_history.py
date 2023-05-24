import uuid

from apps.activities.crud import ActivityItemHistoriesCRUD
from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.activities.domain.activity_full import ActivityItemFull
from apps.activities.domain.activity_item_history import ActivityItemHistory


class ActivityItemHistoryService:
    def __init__(self, session, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version
        self.session = session

    async def add(self, activity_items: list[ActivityItemFull]):
        schemas = []

        for item in activity_items:
            schemas.append(
                ActivityItemHistorySchema(
                    id=item.id,
                    id_version=f"{item.id}_{self.version}",
                    activity_id=f"{item.activity_id}_{self.version}",
                    question=item.question,
                    response_type=item.response_type,
                    response_values=item.response_values.dict()
                    if item.response_values
                    else None,
                    config=item.config.dict(),
                    order=item.order,
                    name=item.name,
                )
            )
        await ActivityItemHistoriesCRUD(self.session).create_many(schemas)

    async def get_by_activity_id(
        self, activity_id: uuid.UUID
    ) -> list[ActivityItemHistory]:
        activity_id_version = f"{activity_id}_{self.version}"
        schemas = await ActivityItemHistoriesCRUD(
            self.session
        ).get_by_activity_id_version(activity_id_version)
        return [ActivityItemHistory.from_orm(schema) for schema in schemas]

    async def get_by_activity_id_versions(
        self, activity_id_versions: list[str]
    ) -> list[ActivityItemHistory]:
        schemas = await ActivityItemHistoriesCRUD(
            self.session
        ).get_by_activity_id_versions(activity_id_versions)
        return [ActivityItemHistory.from_orm(schema) for schema in schemas]
