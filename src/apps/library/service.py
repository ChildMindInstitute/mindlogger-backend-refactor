import uuid

from apps.activities.crud import (
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
)
from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD
from apps.library.crud import LibraryCRUD
from apps.library.db import LibrarySchema
from apps.library.domain import (
    AppletLibraryCreate,
    AppletLibraryFull,
    LibraryItem,
    LibraryItemActivity,
    LibraryItemActivityItem,
    PublicLibraryItem,
)
from apps.library.errors import AppletNameExistsError, AppletVersionExistsError


class LibraryService:
    def __init__(self, session):
        self.session = session

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
        # check if this applet version is already in library
        library_item = await LibraryCRUD(self.session).exist_by_key(
            key="applet_id_version", val=f"{schema.applet_id}_{applet.version}"
        )
        if library_item:
            raise AppletVersionExistsError()

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
        return AppletLibraryFull.from_orm(library_item)

    async def get_all_applets(self) -> list[PublicLibraryItem]:
        """Get all applets for library."""

        library_items = await LibraryCRUD(self.session).get_all_library_items()

        for library_item in library_items:
            library_item = await self._get_full_library_item(library_item)

        return [
            PublicLibraryItem(
                version=library_item.applet_id_version.split("_")[1],
                **library_item.dict(exclude={"applet_id_version"}),
            )
            for library_item in library_items
        ]

    async def get_applet_by_id(self, id_: uuid.UUID) -> PublicLibraryItem:
        """Get applet detail for library by id."""

        library_item = await LibraryCRUD(self.session).get_library_item_by_id(
            id_
        )

        library_item = await self._get_full_library_item(library_item)
        return PublicLibraryItem(
            version=library_item.applet_id_version.split("_")[1],
            **library_item.dict(exclude={"applet_id_version"}),
        )

    async def _get_full_library_item(
        self, library_item: LibraryItem
    ) -> LibraryItem:
        activities = await ActivityHistoriesCRUD(
            session=self.session
        ).retrieve_by_applet_version(library_item.applet_id_version)

        library_item_activities = []
        for activity in activities:
            activity_items = await ActivityItemHistoriesCRUD(
                session=self.session
            ).get_by_activity_id_version(activity_id=activity.id_version)

            library_item_activities.append(
                LibraryItemActivity(
                    name=activity.name,
                    items=[
                        LibraryItemActivityItem(
                            name=item.name,
                            question=item.question,
                            response_type=item.response_type,
                            response_values=self._get_response_value_options(
                                item.response_values
                            ),
                            order=item.order,
                        )
                        for item in activity_items
                    ],
                )
            )
        library_item.activities = library_item_activities

        return library_item

    def _get_response_value_options(self, response_values):
        if response_values:
            if "options" in response_values:
                return [
                    option["text"] for option in response_values["options"]
                ]
        return None
