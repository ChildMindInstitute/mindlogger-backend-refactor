import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import distinct, or_, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.applets import errors
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import Role
from apps.applets.domain.applet import AppletDataRetention
from apps.applets.errors import AppletNotFoundError
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.workspaces.db.schemas import UserAppletAccessSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class _AppletFiltering(Filtering):
    owner_id = FilterField(AppletSchema.id, method_name="filter_by_owner")

    def filter_by_owner(self, field, value: uuid.UUID):
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(UserAppletAccessSchema.user_id == value)
        query = query.where(UserAppletAccessSchema.role == Role.ADMIN)
        return field.in_(query)


class _AppletSearching(Searching):
    search_fields = [AppletSchema.display_name]


class _AppletOrdering(Ordering):
    id = AppletSchema.id
    display_name = AppletSchema.display_name
    created_at = AppletSchema.created_at
    updated_at = AppletSchema.updated_at


class AppletsCRUD(BaseCRUD[AppletSchema]):
    schema_class = AppletSchema

    async def save(self, schema: AppletSchema) -> AppletSchema:
        """Return applets instance and the created information."""

        instance: AppletSchema = await self._create(schema)
        return instance

    async def update_by_id(
        self, pk: uuid.UUID, schema: AppletSchema
    ) -> AppletSchema:
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=schema,
        )
        return instance

    async def get_by_display_name(
        self,
        display_name: str,
        applet_ids: Query | list[uuid.UUID],
        exclude_id: uuid.UUID | None,
    ) -> list[AppletSchema]:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.display_name == display_name)
        query = query.where(AppletSchema.id.in_(applet_ids))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        if exclude_id:
            query = query.where(AppletSchema.id != exclude_id)
        db_result = await self._execute(query)
        results = db_result.scalars().all()
        return results

    async def get_by_link(
        self, link: uuid.UUID, require_login: bool
    ) -> AppletSchema | None:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.link == link)
        query = query.where(AppletSchema.require_login == require_login)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def _fetch(self, key: str, value: Any) -> AppletSchema:
        """Fetch applets by id or display_name from the database."""

        if key not in {"id", "display_name"}:
            raise errors.AppletsError(
                f"Can not make the looking up applets by {key} {value}"
            )

        # Get applets from the database
        if not (instance := await self._get(key, value)):
            raise errors.AppletNotFoundError(key=key, value=value)

        return instance

    async def get_by_id(self, id_: uuid.UUID) -> AppletSchema:
        instance = await self._fetch(key="id", value=id_)
        return instance

    async def exist_by_id(self, id_: uuid.UUID) -> bool:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.id == id_)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def get_applets_by_roles(
        self, user_id: uuid.UUID, roles: list[str], query_params: QueryParams
    ) -> list[AppletSchema]:
        accessible_applets_query = select(UserAppletAccessSchema.applet_id)
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.user_id == user_id
        )
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.role.in_(roles)
        )

        query = select(AppletSchema)
        if query_params.filters:
            query = query.where(
                *_AppletFiltering().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletSearching().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_AppletOrdering().get_clauses(*query_params.ordering)
            )
        query = query.where(AppletSchema.id.in_(accessible_applets_query))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        query = paging(query, query_params.page, query_params.limit)
        result: Result = await self._execute(query)
        return result.scalars().all()

    async def get_applets_by_roles_count(
        self, user_id: uuid.UUID, roles: list[str], query_params: QueryParams
    ) -> int:
        accessible_applets_query = select(UserAppletAccessSchema.applet_id)
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.user_id == user_id
        )
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.role.in_(roles)
        )

        query = select(count(AppletSchema.id))
        if query_params.filters:
            query = query.where(
                *_AppletFiltering().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletSearching().get_clauses(query_params.search)
            )
        query = query.where(AppletSchema.id.in_(accessible_applets_query))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        result: Result = await self._execute(query)
        return result.scalars().first() or 0

    async def get_applet_by_roles(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, roles: list[str]
    ) -> AppletSchema | None:
        query = select(AppletSchema)
        query = query.join_from(UserAppletAccessSchema, AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.limit(1)
        result: Result = await self._execute(query)
        return result.scalars().first()

    async def delete_by_id(self, id_: uuid.UUID):
        """Delete applets by id."""

        query = update(AppletSchema)
        query = query.where(AppletSchema.id == id_)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def check_folder(self, folder_id: uuid.UUID) -> bool:
        """
        Checks whether folder has applets
        """
        query: Query = select(AppletSchema.id)
        query = query.where(AppletSchema.folder_id == folder_id)
        query = query.limit(1)
        query = query.exists()
        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def set_applets_folder(
        self, applet_id: uuid.UUID, folder_id: uuid.UUID | None
    ) -> AppletSchema:
        query = update(AppletSchema)
        query = query.values(folder_id=folder_id)
        query = query.where(AppletSchema.id == applet_id)
        query = query.returning(self.schema_class)
        db_result = await self._execute(query)

        return db_result.scalars().one_or_none()

    async def get_name_duplicates(
        self,
        user_id: uuid.UUID,
        name: str,
        exclude_applet_id: uuid.UUID | None = None,
    ) -> list[str]:
        query: Query = select(distinct(AppletSchema.display_name))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        if exclude_applet_id:
            query = query.where(AppletSchema.id != exclude_applet_id)
        query = query.where(
            or_(
                AppletSchema.display_name.op("~")(f"{name} \\(\\d+\\)"),
                AppletSchema.display_name == name,
            )
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def create_access_link(
        self, applet_id: uuid.UUID, require_login: bool
    ) -> str:
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(link=uuid.uuid4(), require_login=require_login)
        query = query.returning(AppletSchema.link)
        db_result = await self._execute(query)
        try:
            return db_result.scalars().one()
        except NoResultFound:
            raise AppletNotFoundError(key='id', value=str(applet_id))

    async def delete_access_link(self, applet_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(link=None, require_login=None)
        await self._execute(query)

    async def pin(self, applet_id: uuid.UUID, folder_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.where(AppletSchema.folder_id == folder_id)
        query = query.values(pinned_at=datetime.now())
        await self._execute(query)

    async def unpin(self, applet_id: uuid.UUID, folder_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.where(AppletSchema.folder_id == folder_id)
        query = query.values(pinned_at=None)
        await self._execute(query)

    async def set_data_retention(
        self, applet_id: uuid.UUID, data_retention: AppletDataRetention
    ):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(
            retention_period=data_retention.period,
            retention_type=data_retention.retention,
        )
        await self._execute(query)
