import uuid

from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD
from apps.library.crud import LibraryCRUD
from apps.library.db import LibrarySchema
from apps.library.domain import AppletLibraryCreate, AppletLibraryFull
from apps.library.errors import AppletNameExistsError


class LibraryService:
    def __init__(self, session, user_id: uuid.UUID):
        self.session = session
        self._user_id = user_id

    async def check_applet_name(self, name: str):
        """Check if applet with this name is already in library."""
        name_exists = await LibraryCRUD(self.session).check_applet_name(name)
        if name_exists:
            raise AppletNameExistsError()

    async def share_applet(self, schema: AppletLibraryCreate):
        """Share applet to library."""

        # check if applet with this name is already in library
        await self.check_applet_name(schema.name)

        # if not, check if library_item.name is same as applet.display_name
        applet = await AppletsCRUD(self.session).get_by_id(
            id_=schema.applet_id
        )
        if applet.display_name != schema.name:
            # if not, update applet.display_name to library_item.name
            # in applet and applet_history
            await AppletsCRUD(self.session).update_display_name(
                applet_id=schema.applet_id, display_name=schema.name
            )

            await AppletHistoriesCRUD(self.session).update_display_name(
                id_version=f"{schema.applet_id}_{applet.version}",
                display_name=schema.name,
            )

        library_item = LibrarySchema(
            applet_id_version=f"{schema.applet_id}_{applet.version}",
            keywords=schema.keywords,
        )
        library_item = await LibraryCRUD(self.session).save(library_item)
        print("library_item", library_item)
        return AppletLibraryFull.from_orm(library_item)
