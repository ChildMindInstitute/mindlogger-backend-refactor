from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.themes.db.schemas import ThemeSchema
from apps.themes.domain import PublicTheme, Theme, ThemeCreate, ThemeUpdate
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

        ALLOWED_FIELDS = {"id"}
        if key not in ALLOWED_FIELDS:
            raise ThemesError(
                f"Can not make the looking up theme by {key} {value}"
            )

        # Get theme from the database
        if not (instance := await self._get(key, value)):
            raise ThemeNotFoundError(f"No such theme with {key}={value}.")

        # Get internal model
        theme: Theme = Theme.from_orm(instance)

        return theme

    async def get_by_id(self, pk: int) -> Theme:
        return await self._fetch(key="id", value=pk)

    async def get_all(self) -> list[PublicTheme]:
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

    async def delete_by_id(self, pk: int, creator_id: int):
        """Delete theme by id."""
        instance: Theme = await self._fetch(key="id", value=pk)

        if instance.creator != creator_id:

            raise ThemePermissionsError(
                "You do not have permissions to delete this theme."
            )
        await self._delete(key="id", value=pk)

    async def update(
        self, pk: int, update_schema: ThemeUpdate, creator_id: int
    ) -> Theme:
        # Update theme in database

        instance: Theme = await self._fetch(key="id", value=pk)

        if instance.creator != creator_id:
            raise ThemePermissionsError(
                "You do not have permissions to update this theme."
            )
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=ThemeSchema(
                name=update_schema.name,
                logo=update_schema.logo,
                background_image=update_schema.background_image,
                primary_color=str(update_schema.primary_color),
                secondary_color=str(update_schema.secondary_color),
                tertiary_color=str(update_schema.tertiary_color),
                public=update_schema.public,
                allow_rename=update_schema.allow_rename,
            ),
        )

        return Theme.from_orm(instance)
