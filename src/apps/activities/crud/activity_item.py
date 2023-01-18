from sqlalchemy import delete, select

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema
from apps.applets.db.schemas import AppletSchema
from infrastructure.database import BaseCRUD


class ActivityItemsCRUD(BaseCRUD[ActivityItemSchema]):
    schema_class = ActivityItemSchema

    async def create_many(
        self,
        activity_item_schemas: list[ActivityItemSchema],
    ) -> list[ActivityItemSchema]:
        instances = await self._create_many(activity_item_schemas)
        return instances

    async def delete_by_applet_id(self, applet_id):
        activity_id_query = select(ActivitySchema.id).where(
            ActivitySchema.applet_id == applet_id
        )
        query = delete(ActivityItemSchema).where(
            ActivityItemSchema.activity_id.in_(activity_id_query)
        )
        await self._execute(query)

    async def get_by_applet_id(self, applet_id) -> list[ActivityItemSchema]:
        query = select(ActivityItemSchema)
        query = query.join(
            ActivitySchema,
            ActivitySchema.id == ActivityItemSchema.activity_id,
        )
        query = query.join(
            AppletSchema,
            AppletSchema.id == ActivitySchema.applet_id,
        )
        query = query.where(AppletSchema.id == applet_id)
        query = query.order_by(
            ActivityItemSchema.ordering.asc(),
        )
        result = await self._execute(query)
        return result.scalars().all()
