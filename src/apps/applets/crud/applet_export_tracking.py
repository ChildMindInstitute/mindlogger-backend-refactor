import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletExportTrackingSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletExportTrackingCRUD"]


class AppletExportTrackingCRUD(BaseCRUD[AppletExportTrackingSchema]):
    schema_class = AppletExportTrackingSchema

    async def create(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> AppletExportTrackingSchema:
        schema = AppletExportTrackingSchema(
            applet_id=applet_id, user_id=user_id
        )
        return await self._create(schema)

    async def get_by_(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> AppletExportTrackingSchema:
        query: Query = select(AppletExportTrackingSchema)
        query = query.where(
            AppletExportTrackingSchema.applet_id == applet_id,
            AppletExportTrackingSchema.user_id == user_id,
        )
        result = await self._execute(query)
        return result.scalars().one_or_none()
