import datetime
import typing
import uuid
from typing import Any, cast

from sqlalchemy import and_, case, distinct, false, literal, null, or_, select, text, true, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count, func

from apps.activities.db.schemas import ActivitySchema
from apps.applets import errors
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import Role
from apps.applets.domain.applet import AppletDataRetention
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.errors import AppletNotFoundError
from apps.folders.db.schemas import FolderAppletSchema, FolderSchema
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.users import UserSchema
from apps.users.db.schemas import UserDeviceSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class _AppletFiltering(Filtering):
    owner_id = FilterField(AppletSchema.id, method_name="filter_by_owner")

    def filter_by_owner(self, field, value: uuid.UUID):
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(UserAppletAccessSchema.user_id == value)
        query = query.where(UserAppletAccessSchema.role == Role.OWNER)
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

    async def update_by_id(self, pk: uuid.UUID, schema: AppletSchema) -> AppletSchema:
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
        query = query.where(AppletSchema.display_name.ilike(display_name))
        query = query.where(AppletSchema.id.in_(applet_ids))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        if exclude_id:
            query = query.where(AppletSchema.id != exclude_id)
        db_result = await self._execute(query)
        results = db_result.scalars().all()
        results = cast(list[AppletSchema], results)
        return results

    async def get_by_link(self, link: uuid.UUID, require_login: bool = False) -> AppletSchema | None:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.link == link)
        query = query.where(AppletSchema.require_login == require_login)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def _fetch(self, key: str, value: Any) -> AppletSchema:
        """Fetch applets by id or display_name from the database."""

        # Get applets from the database
        if not (instance := await self._get(key, value)):
            raise errors.AppletNotFoundError(key=key, value=value)

        return instance

    async def get_by_id(self, id_: uuid.UUID) -> AppletSchema:
        instance = await self._fetch(key="id", value=id_)
        return instance

    async def get_by_ids(self, ids: typing.Iterable[uuid.UUID]) -> list[AppletSchema]:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.id.in_(ids))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def exist_by_id(self, id_: uuid.UUID) -> bool:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.id == id_)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def get_applets_by_roles(
        self,
        user_id: uuid.UUID,
        roles: list[Role],
        query_params: QueryParams,
        exclude_without_encryption: bool = False,
    ) -> list[AppletSchema]:
        accessible_applets_query = select(UserAppletAccessSchema.applet_id)
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.user_id == user_id)
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.role.in_(roles))
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.soft_exists())

        query = select(AppletSchema)
        if query_params.filters:
            query = query.where(*_AppletFiltering().get_clauses(**query_params.filters))
        if query_params.search:
            query = query.where(_AppletSearching().get_clauses(query_params.search))
        if query_params.ordering:
            query = query.order_by(*_AppletOrdering().get_clauses(*query_params.ordering))
        query = query.where(AppletSchema.id.in_(accessible_applets_query))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        if exclude_without_encryption:
            query = query.where(
                func.jsonb_typeof(AppletSchema.encryption) != text("'null'"),
            )
        query = paging(query, query_params.page, query_params.limit)
        result: Result = await self._execute(query)
        return result.scalars().all()

    async def get_applets_by_roles_count(
        self,
        user_id: uuid.UUID,
        roles: list[str],
        query_params: QueryParams,
        exclude_without_encryption: bool = False,
    ) -> int:
        accessible_applets_query = select(UserAppletAccessSchema.applet_id)
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.user_id == user_id)
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.role.in_(roles))
        accessible_applets_query = accessible_applets_query.where(UserAppletAccessSchema.soft_exists())

        query = select(count(AppletSchema.id))
        if query_params.filters:
            query = query.where(*_AppletFiltering().get_clauses(**query_params.filters))
        if query_params.search:
            query = query.where(_AppletSearching().get_clauses(query_params.search))
        query = query.where(AppletSchema.id.in_(accessible_applets_query))
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        if exclude_without_encryption:
            query = query.where(
                func.jsonb_typeof(AppletSchema.encryption) != text("'null'"),
            )
        result: Result = await self._execute(query)
        return result.scalars().first() or 0

    async def get_applet_by_roles(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, roles: list[Role]
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

    async def get_name_duplicates(
        self,
        user_id: uuid.UUID,
        name: str,
        exclude_applet_id: uuid.UUID | None = None,
    ) -> list[str]:
        name = name.lower()
        query: Query = select(distinct(AppletSchema.display_name))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        if exclude_applet_id:
            query = query.where(AppletSchema.id != exclude_applet_id)
        query = query.where(
            or_(
                func.lower(AppletSchema.display_name).op("~")(f"{name} \\(\\d+\\)"),
                func.lower(AppletSchema.display_name) == name,
            )
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def create_access_link(self, applet_id: uuid.UUID, require_login: bool) -> str:
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(link=uuid.uuid4(), require_login=require_login)
        query = query.returning(AppletSchema.link)
        db_result = await self._execute(query)
        try:
            return db_result.scalars().one()
        except NoResultFound:
            raise AppletNotFoundError(key="id", value=str(applet_id))

    async def delete_access_link(self, applet_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(link=None, require_login=None)
        await self._execute(query)

    async def set_data_retention(self, applet_id: uuid.UUID, data_retention: AppletDataRetention):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(
            retention_period=data_retention.period,
            retention_type=data_retention.retention,
        )
        await self._execute(query)

    async def publish_by_id(self, applet_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(is_published=True)

        await self._execute(query)

    async def conceal_by_id(self, applet_id: uuid.UUID):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(is_published=False)

        await self._execute(query)

    async def set_report_configuration(self, applet_id: uuid.UUID, schema: AppletReportConfiguration):
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(
            report_server_ip=schema.report_server_ip,
            report_public_key=schema.report_public_key,
            report_recipients=schema.report_recipients,
            report_include_user_id=schema.report_include_user_id,
            report_include_case_id=schema.report_include_case_id,
            report_email_body=schema.report_email_body,
        )

        await self._execute(query)

    async def get_folders_applets(
        self, owner_id: uuid.UUID, user_id: uuid.UUID, folder_id: uuid.UUID
    ) -> list[tuple[AppletSchema, bool]]:
        access_query: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.user_id)
        access_query = access_query.distinct(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.user_id)
        access_query = access_query.where(UserAppletAccessSchema.owner_id == owner_id)
        access_query = access_query.where(UserAppletAccessSchema.user_id == user_id)
        access_query = access_query.where(UserAppletAccessSchema.soft_exists())
        access_query = access_query.alias("access_query")

        query: Query = select(
            AppletSchema,
            case(
                (FolderAppletSchema.pinned_at != None, true()),  # noqa
                else_=false(),
            ),
        )
        query = query.join(access_query, access_query.c.applet_id == AppletSchema.id)
        query = query.join(
            FolderAppletSchema,
            and_(
                FolderAppletSchema.applet_id == AppletSchema.id,
                FolderAppletSchema.folder_id == folder_id,
            ),
            isouter=True,
        )
        query = query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        query = query.where(FolderSchema.creator_id == user_id)
        query = query.where(access_query.c.user_id == user_id)
        query = query.order_by(
            case(
                (FolderAppletSchema.pinned_at != None, true()),  # noqa
                else_=false(),
            ).desc(),
            FolderAppletSchema.pinned_at.desc(),
            AppletSchema.created_at.desc(),
        )

        db_result = await self._execute(query)
        return db_result.all()

    @staticmethod
    async def _folder_list_query(owner_id: uuid.UUID, user_id: uuid.UUID):
        workspace_applets_query: Query = select(
            func.count(FolderAppletSchema.id).label("applet_count"),
            FolderAppletSchema.folder_id,
        )
        workspace_applets_query = workspace_applets_query.join(
            AppletSchema,
            AppletSchema.id == FolderAppletSchema.applet_id,
        )
        workspace_applets_query = workspace_applets_query.join(
            FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id
        )
        workspace_applets_query = workspace_applets_query.where(
            FolderSchema.workspace_id == owner_id,
            AppletSchema.is_deleted.is_(False),
        )
        workspace_applets_query = workspace_applets_query.group_by(FolderAppletSchema.folder_id)
        workspace_applets_query = workspace_applets_query.alias("workspace_applets")
        folders_query: Query = select(
            FolderSchema.id.label("id"),
            FolderSchema.name.label("name"),
            literal("").label("image"),
            false().label("is_pinned"),
            null().label("encryption"),
            FolderSchema.created_at.label("created_at"),
            FolderSchema.updated_at.label("updated_at"),
            literal("").label("version"),
            literal("folder").label("type"),
            null().label("role"),
            func.coalesce(workspace_applets_query.c.applet_count, 0).label("folders_applet_count"),
            literal("1").label("ordering"),
            null().label("description"),
            null().label("activity_count"),
        )
        folders_query = folders_query.where(FolderSchema.creator_id == user_id)
        folders_query = folders_query.join(
            workspace_applets_query,
            workspace_applets_query.c.folder_id == FolderSchema.id,
            isouter=True,
        )

        folders_query = folders_query.where(FolderSchema.workspace_id == owner_id)
        return folders_query

    async def get_workspace_applets(
        self, owner_id: uuid.UUID, user_id: uuid.UUID, filters: QueryParams
    ) -> list[
        tuple[
            uuid.UUID,
            str,
            str,
            bool,
            dict | None,
            datetime.datetime,
            datetime.datetime,
            str,
            str,
            str,
            str,
            str,
            dict,
            int,
        ]
    ]:
        access_subquery: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.role)
        access_subquery = access_subquery.where(
            and_(
                UserAppletAccessSchema.soft_exists(),
                UserAppletAccessSchema.role != Role.RESPONDENT,
            )
        )

        access_subquery = access_subquery.order_by(
            UserAppletAccessSchema.applet_id.asc(),
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc(),
        )
        access_subquery = access_subquery.where(UserAppletAccessSchema.owner_id == owner_id)
        access_subquery = access_subquery.where(UserAppletAccessSchema.user_id == user_id)
        access_subquery = access_subquery.subquery().alias("access_sub_query")

        access_query: Query = select(access_subquery)
        access_query = access_query.distinct(access_subquery.c.applet_id)
        access_query = access_query.alias("access_query")

        folder_applets_query: Query = select(FolderAppletSchema.applet_id)
        folder_applets_query = folder_applets_query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        folder_applets_query = folder_applets_query.where(FolderSchema.creator_id == user_id)
        activity_subquery = self._get_activity_subquery()
        query: Query = select(
            AppletSchema.id.label("id"),
            AppletSchema.display_name.label("name"),
            AppletSchema.image.label("image"),
            false().label("is_pinned"),
            AppletSchema.encryption.label("encryption"),
            AppletSchema.created_at.label("created_at"),
            AppletSchema.updated_at.label("updated_at"),
            AppletSchema.version.label("version"),
            literal("applet").label("type"),
            access_query.c.role.label("role"),
            literal(0).label("folders_applet_count"),
            literal("2").label("ordering"),
            AppletSchema.description,
            activity_subquery,
        )
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=False,
        )
        query = query.where(
            AppletSchema.id.notin_(folder_applets_query),
        )
        folders_query = await self._folder_list_query(owner_id, user_id)
        query = folders_query.union(query)

        cte = query.cte("applets")
        query = select(cte)

        orderings = type(
            "_Ordering",
            (Ordering,),
            {
                "display_name": cte.c.name,
                "created_at": cte.c.created_at,
                "updated_at": cte.c.updated_at,
            },
        )()

        query = query.order_by(
            cte.c.ordering.asc(),
            *orderings.get_clauses(*filters.ordering),
        )

        query_paged = paging(query, filters.page, filters.limit)
        db_result = await self._execute(query_paged)
        return db_result

    async def search_workspace_applets(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
        search_text: str,
        filters: QueryParams,
    ) -> list[
        tuple[
            uuid.UUID,
            str,
            str,
            dict | None,
            datetime.datetime,
            datetime.datetime,
            str,
            str,
            uuid.UUID,
            str,
        ]
    ]:
        folders_query: Query = select(FolderAppletSchema.applet_id, FolderSchema.id, FolderSchema.name)
        folders_query = folders_query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        folders_query = folders_query.where(FolderSchema.creator_id == user_id)
        folders_query = folders_query.where(FolderSchema.workspace_id == owner_id)

        folders_query = folders_query.alias("folders")

        access_subquery: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.role)
        access_subquery = access_subquery.where(UserAppletAccessSchema.soft_exists())
        access_subquery = access_subquery.order_by(
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc()
        )
        access_subquery = access_subquery.where(UserAppletAccessSchema.owner_id == owner_id)
        access_subquery = access_subquery.where(UserAppletAccessSchema.user_id == user_id)
        access_subquery = access_subquery.subquery().alias("access_sub_query")

        access_query: Query = select(access_subquery)
        access_query = access_query.distinct(access_subquery.c.applet_id)
        access_query = access_query.alias("access_query")

        query: Query = select(
            AppletSchema.id.label("id"),
            AppletSchema.display_name.label("name"),
            AppletSchema.image.label("image"),
            AppletSchema.encryption.label("encryption"),
            AppletSchema.created_at.label("created_at"),
            AppletSchema.updated_at.label("updated_at"),
            AppletSchema.version.label("version"),
            access_query.c.role.label("role"),
            folders_query.c.id.label("folder_id"),
            folders_query.c.name.label("folder_name"),
        )
        query = query.join(
            folders_query,
            folders_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=False,
        )
        query = query.where(_AppletSearching().get_clauses(search_text))
        query = query.where(access_query.c.role != None)  # noqa

        if "updatedAt" in filters.ordering:
            query = query.order_by(AppletSchema.updated_at.asc())
        else:
            query = query.order_by(AppletSchema.updated_at.desc())

        query = paging(query, filters.page, filters.limit)

        db_result = await self._execute(query)
        return db_result.all()

    async def search_workspace_applets_count(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
        search_text: str,
    ) -> int:
        folders_query: Query = select(FolderAppletSchema.applet_id, FolderSchema.id, FolderSchema.name)
        folders_query = folders_query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        folders_query = folders_query.where(FolderSchema.creator_id == user_id)
        folders_query = folders_query.where(FolderSchema.workspace_id == owner_id)

        folders_query = folders_query.alias("folders")

        access_subquery: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.role)
        access_subquery = access_subquery.where(UserAppletAccessSchema.soft_exists())
        access_subquery = access_subquery.order_by(
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc()
        )
        access_subquery = access_subquery.where(UserAppletAccessSchema.owner_id == owner_id)
        access_subquery = access_subquery.where(UserAppletAccessSchema.user_id == user_id)
        access_subquery = access_subquery.subquery().alias("access_sub_query")

        access_query: Query = select(access_subquery)
        access_query = access_query.distinct(access_subquery.c.applet_id)
        access_query = access_query.alias("access_query")

        query: Query = select(AppletSchema.id.label("id"))
        query = query.join(
            folders_query,
            folders_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.where(_AppletSearching().get_clauses(search_text))
        query = query.where(access_query.c.role != None)  # noqa
        query = query.subquery()
        db_result = await self._execute(select(func.count(query.c.id)))
        return db_result.scalars().first() or 0

    async def get_workspace_applets_count(self, owner_id: uuid.UUID, user_id: uuid.UUID) -> int:
        workspace_applets_query: Query = select(
            FolderAppletSchema.folder_id,
        )
        workspace_applets_query = workspace_applets_query.join(
            FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id
        )
        workspace_applets_query = workspace_applets_query.where(FolderSchema.workspace_id == owner_id)
        workspace_applets_query = workspace_applets_query.group_by(FolderAppletSchema.folder_id)
        workspace_applets_query = workspace_applets_query.alias("workspace_applets")

        folders_query: Query = select(FolderSchema.id.label("id"))
        folders_query = folders_query.where(FolderSchema.creator_id == user_id)
        folders_query = folders_query.join(
            workspace_applets_query,
            workspace_applets_query.c.folder_id == FolderSchema.id,
            isouter=True,
        )
        folders_query = folders_query.where(FolderSchema.workspace_id == owner_id)

        access_subquery: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.role)
        access_subquery = access_subquery.where(
            UserAppletAccessSchema.is_deleted == False  # noqa
        )
        access_subquery = access_subquery.order_by(
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc()
        )
        access_subquery = access_subquery.where(UserAppletAccessSchema.owner_id == owner_id)
        access_subquery = access_subquery.where(UserAppletAccessSchema.user_id == user_id)
        access_subquery = access_subquery.subquery().alias("access_sub_query")

        access_query: Query = select(access_subquery)
        access_query = access_query.distinct(access_subquery.c.applet_id)
        access_query = access_query.alias("access_query")

        folder_applets_query: Query = select(FolderAppletSchema.applet_id)
        folder_applets_query = folder_applets_query.join(FolderSchema, FolderSchema.id == FolderAppletSchema.folder_id)
        folder_applets_query = folder_applets_query.where(FolderSchema.creator_id == user_id)

        query: Query = select(AppletSchema.id.label("id"))
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.where(AppletSchema.id.notin_(folder_applets_query))
        query = query.where(access_query.c.role != None)  # noqa

        query_union: Query = folders_query.union(query)
        query_union = query_union.subquery()
        db_result = await self._execute(select(func.count(query_union.c.id)))
        return db_result.scalars().first() or 0

    async def update_display_name(self, applet_id: uuid.UUID, display_name: str) -> None:
        query: Query = update(AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.values(
            display_name=display_name,
        )
        await self._execute(query)

    async def get_respondents_device_ids(
        self,
        applet_id: uuid.UUID,
        respondent_ids: list[uuid.UUID] | None = None,
    ) -> list[str]:
        query: Query = select(UserDeviceSchema.device_id)
        query = query.join(UserSchema, UserSchema.id == UserDeviceSchema.user_id)
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        if respondent_ids:
            query = query.where(UserAppletAccessSchema.user_id.in_(respondent_ids))
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.is_deleted == False)  # noqa

        db_result = await self._execute(query)
        return db_result.scalars().all()

    @staticmethod
    def _get_activity_subquery() -> Query:
        return (
            select([func.count().label("count")])
            .where(
                AppletSchema.id == ActivitySchema.applet_id,
            )
            .scalar_subquery()
        )

    @staticmethod
    def _get_access_subquery(owner_id: uuid.UUID, user_id: uuid.UUID) -> Query:
        access_subquery: Query = select(UserAppletAccessSchema.applet_id, UserAppletAccessSchema.role)
        access_subquery = access_subquery.where(UserAppletAccessSchema.soft_exists())
        access_subquery = access_subquery.order_by(
            UserAppletAccessSchema.applet_id.asc(),
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc(),
        )
        access_subquery = access_subquery.where(UserAppletAccessSchema.owner_id == owner_id)
        access_subquery = access_subquery.where(UserAppletAccessSchema.user_id == user_id)
        access_subquery = access_subquery.subquery().alias("access_sub_query")

        access_query: Query = select(access_subquery)
        access_query = access_query.distinct(access_subquery.c.applet_id)
        access_query = access_query.alias("access_query")
        return access_query

    async def get_applets_flat_list(self, owner_id: uuid.UUID, user_id: uuid.UUID, filters: QueryParams):
        access_query = self._get_access_subquery(owner_id, user_id)
        activity_subquery = self._get_activity_subquery()
        query: Query = select(
            AppletSchema.id.label("id"),
            AppletSchema.display_name.label("name"),
            AppletSchema.image.label("image"),
            false().label("is_pinned"),
            AppletSchema.encryption.label("encryption"),
            AppletSchema.created_at.label("created_at"),
            AppletSchema.updated_at.label("updated_at"),
            AppletSchema.version.label("version"),
            literal("applet").label("type"),
            access_query.c.role.label("role"),
            literal(0).label("folders_applet_count"),
            literal("2").label("ordering"),
            AppletSchema.description,
            activity_subquery,
        )
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.where(
            access_query.c.role != None,  # noqa
            AppletSchema.is_deleted.is_(False),
        )
        query_cte = query.cte("applets")
        query = select(query_cte)

        class _Ordering(Ordering):
            display_name = query_cte.c.name
            created_at = query_cte.c.created_at

        query = query.order_by(
            query_cte.c.ordering.asc(),
            *_Ordering().get_clauses(*filters.ordering),
        )

        query = paging(query, filters.page, filters.limit)
        db_result = await self._execute(query)
        return db_result.all()

    async def get_workspace_applets_flat_list_count(self, owner_id: uuid.UUID, user_id: uuid.UUID) -> int:
        access_query = self._get_access_subquery(owner_id, user_id)
        query: Query = select(AppletSchema.id.label("id"))
        query = query.join(
            access_query,
            access_query.c.applet_id == AppletSchema.id,
            isouter=True,
        )
        query = query.where(access_query.c.role != None)  # noqa
        query = query.subquery()
        db_result = await self._execute(select(func.count(query.c.id)))
        return db_result.scalars().first() or 0

    async def has_assessment(self, applet_id: uuid.UUID) -> bool:
        query: Query = select(ActivitySchema.id)
        query = query.where(ActivitySchema.applet_id == applet_id)
        query = query.where(ActivitySchema.is_reviewable.is_(True))
        query = query.exists()
        result = await self._execute(select(query))
        return bool(result.scalars().first())
