from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.authentication.errors import PermissionsError
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.themes.db.schemas import ThemeSchema
from apps.themes.domain import PublicTheme, Theme, ThemeCreate, ThemeUpdate
from apps.themes.errors import (
    ThemeAlreadyExist,
    ThemeNotFoundError,
    ThemesError,
)
from infrastructure.database.crud import BaseCRUD

__all__ = ["ThemesCRUD"]


class _ThemeFiltering(Filtering):
    public = FilterField(ThemeSchema.public)
    allow_rename = FilterField(ThemeSchema.allow_rename)
    creator = FilterField(ThemeSchema.creator)


class _ThemeSearching(Searching):
    search_fields = [ThemeSchema.name]


class _ThemeOrdering(Ordering):
    id = ThemeSchema.id
    name = ThemeSchema.name
    created_at = ThemeSchema.created_at
    updated_at = ThemeSchema.updated_at


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
            raise ThemeNotFoundError(key, value)

        # Get internal model
        theme: Theme = Theme.from_orm(instance)

        return theme

    async def get_by_id(self, pk: int) -> Theme:
        return await self._fetch(key="id", value=pk)

    async def list(self, query_params: QueryParams) -> list[PublicTheme]:
        query: Query = select(self.schema_class)
        if query_params.filters:
            query = query.where(
                *_ThemeFiltering().get_clauses(**query_params.filters)
            )
        if query_params.ordering:
            query = query.order_by(
                *_ThemeOrdering().get_clauses(*query_params.ordering)
            )
        if query_params.search:
            query = query.where(
                _ThemeSearching().get_clauses(query_params.search)
            )
        query = query.offset(query_params.page - 1)
        query = query.limit(query_params.limit)

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
            raise PermissionsError(
                "You do not have permissions to delete this theme."
            )
        await self._delete(key="id", value=pk)

    async def update(
        self, pk: int, update_schema: ThemeUpdate, creator_id: int
    ) -> Theme:
        # Update theme in database

        instance: Theme = await self._fetch(key="id", value=pk)

        if instance.creator != creator_id:
            raise PermissionsError(
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
