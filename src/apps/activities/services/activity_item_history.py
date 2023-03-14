import uuid

from apps.activities.crud import ActivityItemHistoriesCRUD
from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.activities.domain.activity_full import ActivityItemFull


class ActivityItemHistoryService:
    def __init__(self, applet_id: uuid.UUID, version: str):
        self.applet_id = applet_id
        self.version = version

    async def add(self, activity_items: list[ActivityItemFull]):
        schemas = []

        for item in activity_items:
            schemas.append(
                ActivityItemHistorySchema(
                    id=item.id,
                    id_version=f"{item.id}_{self.version}",
                    activity_id=f"{item.activity_id}_{self.version}",
                    header_image=item.header_image,
                    question=item.question,
                    response_type=item.response_type,
                    answers=item.answers,
                    config=item.config,
                    ordering=item.ordering,
                )
            )
        await ActivityItemHistoriesCRUD().create_many(schemas)
