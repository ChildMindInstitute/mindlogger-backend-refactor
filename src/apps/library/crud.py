from apps.library.db.schemas import LibrarySchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoriesCRUD"]


class LibraryCRUD(BaseCRUD[LibrarySchema]):
    schema_class = LibrarySchema

    async def save(self, schema: LibrarySchema):
        await self._create(schema)

    async def get_by_id(self, id: str) -> LibrarySchema | None:
        schema = await self._get("id", id)
        return schema

    async def get_all(self) -> list[LibrarySchema] | None:
        query = self._select()
        result = await self._execute(query)
        return result.all()
