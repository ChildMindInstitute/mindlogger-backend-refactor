from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityHistorySchema
from apps.applets.db.schemas import AppletHistorySchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityHistoriesCRUD"]


class ActivityHistoriesCRUD(BaseCRUD[ActivityHistorySchema]):
    schema_class = ActivityHistorySchema

    async def create_many(
        self,
        activities: list[ActivityHistorySchema],
    ):
        await self._create_many(activities)

    async def retrieve_by_applet_version(
        self, id_version
    ) -> list[ActivityHistorySchema]:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.applet_id == id_version)
        query = query.order_by(ActivityHistorySchema.ordering.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_by_applet_ids(
        self, applet_versions: list[str]
    ) -> list[ActivityHistorySchema]:
        """
        retrieve activities by applet id_version fields
        order by id
        """
        query: Query = select(ActivityHistorySchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(
            AppletHistorySchema.id_version.in_(applet_versions)
        )
        query = query.order_by(
            ActivityHistorySchema.id.asc(),
            ActivityHistorySchema.updated_at.asc(),
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()
