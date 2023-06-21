from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletHistorySchema
from apps.library.db.schemas import LibrarySchema
from infrastructure.database.crud import BaseCRUD


class LibraryCRUD(BaseCRUD[LibrarySchema]):
    schema_class = LibrarySchema

    async def save(self, schema: LibrarySchema):
        return await self._create(schema)

    async def get_by_id(self, id: str) -> LibrarySchema | None:
        schema = await self._get("id", id)
        return schema

    async def get_all(self) -> list[LibrarySchema] | None:
        query = select(LibrarySchema)
        result = await self._execute(query)
        return result.all()

    async def delete_by_id(self, id: str) -> None:
        query = delete(LibrarySchema).where(LibrarySchema.id == id)
        await self._execute(query)

    async def check_applet_name(self, name: str):
        query: Query = select(AppletHistorySchema.display_name)
        query = query.join(
            LibrarySchema,
            LibrarySchema.applet_id_version == AppletHistorySchema.id_version,
        )
        query = query.where(AppletHistorySchema.display_name == name)
        query = query.exists()

        result = await self._execute(select(query))

        return result.scalars().first()
