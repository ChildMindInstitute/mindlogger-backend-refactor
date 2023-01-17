from sqlalchemy import select
from sqlalchemy.orm import Query, joinedload

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.applets.domain import detailing_history
from infrastructure.database import BaseCRUD


class ActivityItemsHistoryCRUD(BaseCRUD[ActivityItemHistorySchema]):
    schema_class = ActivityItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityItemHistorySchema],
    ):
        await self._create_many(items)

    async def list_by_applet_id_version(
        self, applet_id_version: str
    ) -> tuple[
        list[detailing_history.Activity], dict[str, detailing_history.Activity]
    ]:
        query: Query = select(ActivityItemHistorySchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == ActivityItemHistorySchema.activity_id,
        )
        query = query.options(joinedload(ActivityItemHistorySchema.activity))
        query = query.filter(
            ActivityHistorySchema.applet_id == applet_id_version
        )
        query = query.order_by(
            ActivityHistorySchema.ordering.asc(),
            ActivityItemHistorySchema.ordering.asc(),
        )

        result = await self._execute(query)
        results = result.scalars().all()
        activities: list[detailing_history.Activity] = []
        activities_map: dict[str, detailing_history.Activity] = dict()

        for item in results:  # type: ActivityItemHistorySchema
            if item.activity_id not in activities_map:
                activity = detailing_history.Activity.from_orm(item.activity)
                activities_map[item.activity_id] = activity
                activities.append(activity)
            activities_map[item.activity_id].items.append(
                detailing_history.ActivityItem.from_orm(item)
            )

        return activities, activities_map
