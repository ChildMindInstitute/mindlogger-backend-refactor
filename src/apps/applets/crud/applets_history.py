from apps.applets.db.schemas import AppletHistorySchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoryCRUD"]


class AppletHistoryCRUD(BaseCRUD[AppletHistorySchema]):
    schema_class = AppletHistorySchema
    initial_version = "1.0.0"
    version_difference = 0.01

    async def save(self, schema: AppletHistorySchema):
        await self._create(schema)
