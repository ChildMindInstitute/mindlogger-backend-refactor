import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.authentication.errors import PermissionsError
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.themes.db.schemas import ThemeSchema
from apps.themes.domain import PublicTheme, Theme
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
    creator_id = FilterField(ThemeSchema.creator_id)


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

    async def get_by_id(self, pk: uuid.UUID) -> Theme:
        return await self._fetch(key="id", value=pk)

    async def get_users_themes_by_ids(
        self, user_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[ThemeSchema]:
        query: Query = select(ThemeSchema)
        query = query.where(ThemeSchema.creator_id == user_id)
        query = query.where(ThemeSchema.id.in_(ids))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[ThemeSchema]:
        query: Query = select(ThemeSchema)
        query = query.where(ThemeSchema.id.in_(ids))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_users_theme_by_id(
        self, user_id: uuid.UUID, them_id: uuid.UUID
    ) -> ThemeSchema:
        query: Query = select(ThemeSchema)
        query = query.where(ThemeSchema.creator_id == user_id)
        query = query.where(ThemeSchema.id == them_id)
        db_result = await self._execute(query)

        return db_result.scalars().one_or_none()

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
        query = paging(query, query_params.page, query_params.limit)

        result: Result = await self._execute(query)
        results: list[PublicTheme] = result.scalars().all()

        return [PublicTheme.from_orm(theme) for theme in results]

    async def save(self, schema: ThemeSchema) -> Theme:
        """Return theme instance and the created information."""
        # Save theme into the database
        try:
            instance: ThemeSchema = await self._create(schema)
        except IntegrityError:
            raise ThemeAlreadyExist()

        # Create internal data model
        theme: Theme = Theme.from_orm(instance)

        return theme

    async def delete_by_id(self, pk: uuid.UUID, creator_id: uuid.UUID):
        """Delete theme by id."""
        instance: Theme = await self._fetch(key="id", value=pk)

        if instance.creator_id != creator_id:
            raise PermissionsError(
                "You do not have permissions to delete this theme."
            )
        await self._delete(key="id", value=pk)

    async def update(
        self, pk: uuid.UUID, update_schema: ThemeSchema, creator_id: uuid.UUID
    ) -> Theme:
        # Update theme in database

        instance: Theme = await self._fetch(key="id", value=pk)

        if instance.creator_id != creator_id:
            raise PermissionsError(
                "You do not have permissions to update this theme."
            )
        try:
            instance = await self._update_one(
                lookup="id", value=pk, schema=update_schema
            )
        except IntegrityError:
            raise ThemeAlreadyExist()

        return Theme.from_orm(instance)

    async def get_by_name_and_creator_id(
        self, name: str, creator_id: uuid.UUID
    ) -> Theme:
        query: Query = select(ThemeSchema)
        query = query.where(ThemeSchema.name == name)
        query = query.where(ThemeSchema.creator_id == creator_id)
        query = query.where(ThemeSchema.is_deleted == False)  # noqa E712

        db_result = await self._execute(query)

        return db_result.scalars().one_or_none()
