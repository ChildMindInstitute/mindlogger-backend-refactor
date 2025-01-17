import datetime
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletSchema
from apps.folders.db.schemas import FolderAppletSchema, FolderSchema
from apps.folders.errors import FolderDoesNotExist
from infrastructure.database import BaseCRUD

__all__ = ["FolderCRUD"]


class FolderCRUD(BaseCRUD):
    schema_class = FolderSchema

    async def get_users_folder_in_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[FolderSchema]:
        workspace_applets_query: Query = select(
            func.count(FolderAppletSchema.id).label("applet_count"),
            FolderAppletSchema.folder_id,
        )
        workspace_applets_query = workspace_applets_query.join(
            FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id
        )

        workspace_applets_query = workspace_applets_query.where(FolderSchema.workspace_id == workspace_id)
        workspace_applets_query = workspace_applets_query.group_by(FolderAppletSchema.folder_id)
        workspace_applets_query = workspace_applets_query.alias("workspace_applets")

        query: Query = select(
            FolderSchema,
            func.coalesce(workspace_applets_query.c.applet_count, 0),
        )
        query = query.join(
            workspace_applets_query,
            workspace_applets_query.c.folder_id == FolderSchema.id,
            isouter=True,
        )
        query = query.where(FolderSchema.workspace_id == workspace_id)
        query = query.order_by(FolderSchema.id.desc())
        query = query.where(FolderSchema.creator_id == user_id)
        query = query.distinct(FolderSchema.id)

        db_result = await self._execute(query)

        schemas = []

        for schema, applet_count in db_result.all():
            schema.applet_count = applet_count
            schemas.append(schema)

        return schemas

    async def save(self, schema: FolderSchema) -> FolderSchema:
        return await self._create(schema)

    async def update_by_id(self, schema: FolderSchema) -> FolderSchema:
        return await self._update_one("id", schema.id, schema)

    async def get_id_of_creators_folder_by_name(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, name: str
    ) -> uuid.UUID | None:
        query: Query = select(FolderSchema.id)
        query = query.where(FolderSchema.workspace_id == workspace_id)
        query = query.where(FolderSchema.creator_id == user_id)
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

    async def delete_creators_folder_by_id(self, creator_id: uuid.UUID, id_: uuid.UUID):
        query: Query = delete(FolderSchema)
        query = query.where(FolderSchema.creator_id == creator_id)
        query = query.where(FolderSchema.id == id_)

        await self._execute(query)

    async def has_applets(self, folder_id: uuid.UUID):
        query: Query = select(FolderAppletSchema.id, AppletSchema.is_deleted)
        query = query.join(AppletSchema, AppletSchema.id == FolderAppletSchema.applet_id)
        query = query.where(
            FolderAppletSchema.folder_id == folder_id,
            AppletSchema.is_deleted.is_(False),
        )
        query = query.exists()

        db_result = await self._execute(select(query))

        return db_result.scalars().first()

    async def pin_applet(self, folder_id: uuid.UUID, applet_id: uuid.UUID):
        query: Query = update(FolderAppletSchema)
        query = query.where(FolderAppletSchema.folder_id == folder_id)
        query = query.where(FolderAppletSchema.applet_id == applet_id)
        query = query.values(pinned_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None))

        await self._execute(query)

    async def unpin_applet(self, folder_id: uuid.UUID, applet_id: uuid.UUID):
        query: Query = update(FolderAppletSchema)
        query = query.where(FolderAppletSchema.folder_id == folder_id)
        query = query.where(FolderAppletSchema.applet_id == applet_id)
        query = query.values(pinned_at=None)

        await self._execute(query)

    async def get_applets_folder_id_in_workspace(
        self, workspace_id: uuid.UUID, applet_id: uuid.UUID
    ) -> list[uuid.UUID]:
        query: Query = select(FolderAppletSchema.folder_id)
        query = query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        query = query.where(FolderSchema.workspace_id == workspace_id)
        query = query.where(FolderAppletSchema.applet_id == applet_id)

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def set_applet_folder(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        folder_id: uuid.UUID | None,
    ):
        folder_query: Query = select(FolderSchema.id)
        folder_query = folder_query.where(FolderSchema.workspace_id == workspace_id)
        folder_query = folder_query.where(FolderSchema.creator_id == user_id)

        query: Query = delete(FolderAppletSchema)
        query = query.where(FolderAppletSchema.applet_id == applet_id)
        query = query.where(FolderAppletSchema.folder_id.in_(folder_query))

        await self._execute(query)

        if folder_id is None:
            return
        await self.save(FolderAppletSchema(folder_id=folder_id, applet_id=applet_id))


class FolderAppletCRUD(BaseCRUD):
    schema_class = FolderAppletSchema

    async def delete_folder_applet_by_applet_id(self, applet_id: uuid.UUID):
        await self._delete(applet_id=applet_id)
