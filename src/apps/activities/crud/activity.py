from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivitySchema
from infrastructure.database import BaseCRUD


class ActivitiesCRUD(BaseCRUD[ActivitySchema]):
    schema_class = ActivitySchema

    async def create_many(
        self,
        activity_schemas: list[ActivitySchema],
    ) -> list[ActivitySchema]:
        instances = await self._create_many(activity_schemas)
        return instances

    async def delete_by_applet_id(self, applet_id):
        query = delete(ActivitySchema).where(
            ActivitySchema.applet_id == applet_id
        )
        await self._execute(query)

    async def get_by_applet_id(self, applet_id: int) -> list[ActivitySchema]:
        query: Query = select(ActivitySchema)
        query = query.where(ActivitySchema.applet_id == applet_id)
        query = query.order_by(ActivitySchema.ordering.asc())
        result = await self._execute(query)
        return result.scalars().all()
