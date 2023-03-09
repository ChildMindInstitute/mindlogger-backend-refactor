import uuid

from apps.themes.crud import ThemesCRUD
from apps.themes.domain import Theme
from apps.themes.errors import ThemeNotFoundError


class ThemeService:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[Theme]:
        themes = await ThemesCRUD().get_users_themes_by_ids(self.user_id, ids)
        return [Theme.from_orm(theme) for theme in themes]

    async def get_by_id(self, theme_id: uuid.UUID) -> Theme:
        theme = await ThemesCRUD().get_users_theme_by_id(
            self.user_id, theme_id
        )
        if not theme:
            raise ThemeNotFoundError("id", str(theme_id))
        return Theme.from_orm(theme)
