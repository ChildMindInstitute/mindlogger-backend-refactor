from apps.logs.db.schemas import UserActivityLogSchema
from infrastructure.database.crud import BaseCRUD


class UserActivityLogCRUD(BaseCRUD[UserActivityLogSchema]):
    schema_class = UserActivityLogSchema

    async def save(self, schema: UserActivityLogSchema) -> UserActivityLogSchema:
        return await self._create(schema)
