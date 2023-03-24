import uuid

from apps.applets.crud import AppletsCRUD
from apps.folders.crud import FolderCRUD
from apps.folders.db.schemas import FolderSchema
from apps.folders.domain import Folder, FolderCreate, FolderUpdate
from apps.folders.errors import (
    AppletNotInFolder,
    FolderAccessDenied,
    FolderAlreadyExist,
    FolderIsNotEmpty,
)


class FolderService:
    def __init__(self, session, user_id: uuid.UUID):
        self._creator_id = user_id
        self.session = session

    async def list(self) -> list[Folder]:
        schemas = await FolderCRUD(self.session).get_creators_folders(
            self._creator_id
        )
        return [Folder.from_orm(schema) for schema in schemas]

    async def create(self, data: FolderCreate) -> Folder:
        await self._validate_create(data.name)
        schema = await FolderCRUD(self.session).save(
            FolderSchema(name=data.name, creator_id=self._creator_id)
        )
        return Folder.from_orm(schema)

    async def _validate_create(self, name: str):
        existed_folder = await FolderCRUD(
            self.session
        ).get_creators_folder_by_name(self._creator_id, name)
        if existed_folder:
            raise FolderAlreadyExist()

    async def update(self, id_: uuid.UUID, data: FolderUpdate) -> Folder:
        await self._validate_update(id_, data.name)
        schema = await FolderCRUD(self.session).update_by_id(
            FolderSchema(id=id_, name=data.name, creator_id=self._creator_id)
        )
        return Folder.from_orm(schema)

    async def _validate_update(self, folder_id, new_name: str):
        await self._validate_folder(folder_id)

        folder_by_new_name = await FolderCRUD(
            self.session
        ).get_creators_folder_by_name(self._creator_id, new_name)
        if folder_by_new_name and folder_by_new_name.id != folder_id:
            raise FolderAlreadyExist()

    async def delete_by_id(self, id_: uuid.UUID):
        await self._validate_delete(id_)
        await FolderCRUD(self.session).delete_creators_folder_by_id(
            self._creator_id, id_
        )

    async def _validate_delete(self, folder_id: uuid.UUID):
        await self._validate_folder(folder_id)

        applet_exists_in_folder = await AppletsCRUD(self.session).check_folder(
            folder_id
        )
        if applet_exists_in_folder:
            raise FolderIsNotEmpty()

    async def pin_applet(self, id_: uuid.UUID, applet_id: uuid.UUID):
        await self._validate_pin(id_, applet_id)
        await AppletsCRUD(self.session).pin(applet_id, id_)

    async def unpin_applet(self, id_: uuid.UUID, applet_id: uuid.UUID):
        await self._validate_pin(id_, applet_id)
        await AppletsCRUD(self.session).unpin(applet_id, id_)

    async def _validate_pin(self, folder_id: uuid.UUID, applet_id: uuid.UUID):
        await self._validate_folder(folder_id)

        # check if applet is in folder
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if applet.folder_id != folder_id:
            raise AppletNotInFolder()

    async def _validate_folder(self, folder_id: uuid.UUID):
        folder = await FolderCRUD(self.session).get_by_id(folder_id)

        if folder.creator_id != self._creator_id:
            raise FolderAccessDenied()
