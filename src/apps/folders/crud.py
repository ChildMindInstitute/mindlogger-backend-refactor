import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.folders.db.schemas import FolderSchema
from apps.folders.errors import FolderDoesNotExist
from infrastructure.database import BaseCRUD

__all__ = ["FolderCRUD"]


class FolderCRUD(BaseCRUD):
    schema_class = FolderSchema

    async def get_creators_folders(
        self, creator_id: uuid.UUID
    ) -> list[FolderSchema]:
        query: Query = select(FolderSchema)
        query = query.where(FolderSchema.creator_id == creator_id)
        query = query.order_by(FolderSchema.id.desc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def save(self, schema: FolderSchema) -> FolderSchema:
        return await self._create(schema)

    async def update_by_id(self, schema: FolderSchema) -> FolderSchema:
        return await self._update_one("id", schema.id, schema)

    async def get_creators_folder_by_name(
        self, creator_id: uuid.UUID, name: str
    ) -> FolderSchema | None:
        query: Query = select(FolderSchema)
        query = query.where(FolderSchema.creator_id == creator_id)
        query = query.where(FolderSchema.name == name)
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_by_id(self, id_: uuid.UUID) -> FolderSchema:
        query: Query = select(FolderSchema)
        query = query.where(FolderSchema.id == id_)
        db_result = await self._execute(query)
        result = db_result.scalars().first()
        if not result:
            raise FolderDoesNotExist()
        return result

    async def delete_creators_folder_by_id(
        self, creator_id: uuid.UUID, id_: uuid.UUID
    ):
        query: Query = delete(FolderSchema)
        query = query.where(FolderSchema.creator_id == creator_id)
        query = query.where(FolderSchema.id == id_)

        await self._execute(query)
