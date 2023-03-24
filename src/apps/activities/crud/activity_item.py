import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityItemsCRUD"]


class ActivityItemsCRUD(BaseCRUD[ActivityItemSchema]):
    schema_class = ActivityItemSchema

    async def create_many(
        self,
        activity_item_schemas: list[ActivityItemSchema],
    ) -> list[ActivityItemSchema]:
        instances = await self._create_many(activity_item_schemas)
        return instances

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        activity_id_query: Query = select(ActivitySchema.id).where(
            ActivitySchema.applet_id == applet_id
        )
        query = delete(ActivityItemSchema).where(
            ActivityItemSchema.activity_id.in_(activity_id_query)
        )
        await self._execute(query)

    async def get_by_activity_id(
        self, activity_id: uuid.UUID
    ) -> list[ActivityItemSchema]:
        query: Query = select(ActivityItemSchema)
        query = query.where(ActivityItemSchema.activity_id == activity_id)
        query = query.order_by(
            ActivityItemSchema.ordering.asc(),
        )
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_id(
        self, activity_item_id: uuid.UUID
    ) -> ActivityItemSchema:
        query: Query = select(ActivityItemSchema)
        query = query.where(ActivityItemSchema.id == activity_item_id)
        result = await self._execute(query)
        return result.scalars().one_or_none()
