from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.themes.db.schemas import ThemeSchema
from apps.themes.domain.themes import (
    PublicTheme,
    Theme,
    ThemeCreate,
    ThemeUpdate,
)
from apps.themes.errors import (
    ThemeAlreadyExist,
    ThemeNotFoundError,
    ThemePermissionsError,
    ThemesError,
)
from infrastructure.database.crud import BaseCRUD

__all__ = ["ThemesCRUD"]


class ThemesCRUD(BaseCRUD[ThemeSchema]):
    schema_class = ThemeSchema

    async def _fetch(self, key: str, value: Any) -> Theme:
        """Fetch theme by id or display_name from the database."""

        if key not in {"id"}:
            raise ThemesError(
                f"Can not make the looking up theme by {key} {value}"
            )

        # Get theme from the database
        if not (instance := await self._get(key, value)):
            raise ThemeNotFoundError(f"No such theme with {key}={value}.")

        # Get internal model
        theme: Theme = Theme.from_orm(instance)

        return theme

    async def get_by_id(self, id_: int) -> Theme:
        return await self._fetch(key="id", value=id_)

    async def all(self) -> list[PublicTheme]:
        query: Query = select(self.schema_class).order_by(self.schema_class.id)

        result: Result = await self._execute(query)
        results: list[PublicTheme] = result.scalars().all()

        return [PublicTheme.from_orm(theme) for theme in results]

    async def save(self, schema: ThemeCreate) -> Theme:
        """Return theme instance and the created information."""

        # Save theme into the database
        try:
            instance: ThemeSchema = await self._create(
                ThemeSchema(**schema.dict())
            )
        except IntegrityError:
            raise ThemeAlreadyExist()

        # Create internal data model
        theme: Theme = Theme.from_orm(instance)

        return theme

    async def delete_by_id(self, id_: int, creator_id: int):
        """Delete theme by id."""
        instance: Theme = await self._fetch(key="id", value=id_)

        if instance.creator != creator_id:

            raise ThemePermissionsError(
                "You do not have permissions to delete this theme."
            )
        await self._delete(key="id", value=id_)

    async def update(
        self, id_: int, update_schema: ThemeUpdate, creator_id: int
    ) -> Theme:
        # Update theme in database

        instance: Theme = await self._fetch(key="id", value=id_)

        if instance.creator != creator_id:
            raise ThemePermissionsError(
                "You do not have permissions to update this theme."
            )
        instance = await self._update(
            lookup="id", value=id_, update_schema=update_schema
        )

        # Create internal data model
        theme = Theme.from_orm(instance)

        return theme
