import uuid
from uuid import UUID

from apps.folders.crud import FolderCRUD
from apps.folders.db.schemas import FolderSchema
from apps.folders.domain import Folder, FolderCreate, FolderUpdate
from apps.folders.errors import AppletNotInFolder, FolderAccessDenied, FolderAlreadyExist, FolderIsNotEmpty


class FolderService:
    def __init__(self, session, workspace_id: UUID, user_id: UUID):
        self._workspace_id = workspace_id
        self._creator_id = user_id
        self.session = session

    async def list(self) -> list[Folder]:
        schemas = await FolderCRUD(self.session).get_users_folder_in_workspace(self._workspace_id, self._creator_id)
        return [Folder.from_orm(schema) for schema in schemas]

    async def create(self, data: FolderCreate) -> Folder:
        await self._validate_create(data.name)
        schema = await FolderCRUD(self.session).save(
            FolderSchema(
                name=data.name,
                creator_id=self._creator_id,
                workspace_id=self._workspace_id,
            )
        )
        return Folder.from_orm(schema)

    async def _validate_create(self, name: str):
        existed_folder = await FolderCRUD(self.session).get_id_of_creators_folder_by_name(
            self._workspace_id, self._creator_id, name
        )
        if existed_folder:
            raise FolderAlreadyExist()

    async def update(self, folder_id: UUID, data: FolderUpdate) -> Folder:
        await self._validate_update(folder_id, data.name)
        schema = await FolderCRUD(self.session).update_by_id(
            FolderSchema(
                id=folder_id,
                name=data.name,
                creator_id=self._creator_id,
                workspace_id=self._workspace_id,
            )
        )
        return Folder.from_orm(schema)

    async def _validate_update(self, folder_id, new_name: str):
        await self._validate_folder(folder_id)

        existed_folder_id = await FolderCRUD(self.session).get_id_of_creators_folder_by_name(
            self._workspace_id, self._creator_id, new_name
        )
        if existed_folder_id and existed_folder_id != folder_id:
            raise FolderAlreadyExist()

    async def delete_by_id(self, folder_id: UUID):
        await self._validate_delete(folder_id)
        await FolderCRUD(self.session).delete_creators_folder_by_id(self._creator_id, folder_id)

    async def _validate_delete(self, folder_id: UUID):
        await self._validate_folder(folder_id)
        has_applets = await FolderCRUD(self.session).has_applets(folder_id)
        if has_applets:
            raise FolderIsNotEmpty()

    async def pin_applet(self, folder_id: UUID, applet_id: UUID):
        await self._validate_pin(folder_id, applet_id)
        await FolderCRUD(self.session).pin_applet(folder_id, applet_id)

    async def unpin_applet(self, folder_id: UUID, applet_id: UUID):
        await self._validate_pin(folder_id, applet_id)
        await FolderCRUD(self.session).unpin_applet(folder_id, applet_id)

    async def _validate_pin(self, folder_id: UUID, applet_id: UUID):
        await self._validate_folder(folder_id)

        # check if applet is in folder
        applets_folders_ids: list[uuid.UUID] = await FolderCRUD(self.session).get_applets_folder_id_in_workspace(
            self._workspace_id, applet_id
        )
        if folder_id not in applets_folders_ids:
            raise AppletNotInFolder()

    async def _validate_folder(self, folder_id: UUID):
        folder = await FolderCRUD(self.session).get_by_id(folder_id)

        if folder.creator_id != self._creator_id:
            raise FolderAccessDenied()

        if folder.workspace_id != self._workspace_id:
            raise FolderAccessDenied()
