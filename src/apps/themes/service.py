import uuid

from apps.shared.query_params import QueryParams
from apps.themes.crud import ThemesCRUD
from apps.themes.domain import (
    PublicTheme,
    Theme,
    ThemeCreate,
    ThemeRequest,
    ThemeUpdate,
)
from apps.themes.errors import ThemeAlreadyExist, ThemeNotFoundError


class ThemeService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[Theme]:
        themes = await ThemesCRUD().get_users_themes_by_ids(self.user_id, ids)
        return [Theme.from_orm(theme) for theme in themes]

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[Theme]:
        themes = await ThemesCRUD().get_by_ids(ids)
        return [Theme.from_orm(theme) for theme in themes]

    async def get_by_id(self, theme_id: uuid.UUID) -> Theme:
        theme = await ThemesCRUD().get_users_theme_by_id(
            self.user_id, theme_id
        )
        if not theme:
            raise ThemeNotFoundError("id", str(theme_id))
        return Theme.from_orm(theme)

    async def create(self, theme_request: ThemeRequest) -> PublicTheme:
        # check name and creator_id combination is unique before save
        if await ThemesCRUD().get_by_name_and_creator_id(
            theme_request.name, self.user_id
        ):
            raise ThemeAlreadyExist(
                f"Theme with name {theme_request.name} already exists"
            )

        theme: Theme = await ThemesCRUD().save(
            schema=ThemeCreate(
                **theme_request.dict(),
                public=False,
                allow_rename=False,
                creator_id=self.user_id,
            )
        )

        return PublicTheme(**theme.dict())

    async def get_all(self, query_params: QueryParams) -> list[PublicTheme]:
        themes: list[PublicTheme] = await ThemesCRUD().list(query_params)

        return themes

    async def delete_by_id(self, theme_id: uuid.UUID) -> None:
        await ThemesCRUD().delete_by_id(pk=theme_id, creator_id=self.user_id)

    async def update(
        self, theme_id: uuid.UUID, theme_request: ThemeRequest
    ) -> PublicTheme:

        theme: Theme = await ThemesCRUD().update(
            pk=theme_id,
            update_schema=ThemeUpdate(
                **theme_request.dict(), public=False, allow_rename=False
            ),
            creator_id=self.user_id,
        )

        return PublicTheme(**theme.dict())
