import asyncio
import uuid
from datetime import datetime
from typing import Tuple

from pydantic import parse_obj_as
from sqlalchemy import (
    and_,
    any_,
    case,
    distinct,
    exists,
    false,
    func,
    literal_column,
    or_,
    select,
    text,
    true,
    update,
)
from sqlalchemy.dialects.postgresql import UUID, aggregate_order_by, insert
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.applets.db.schemas import AppletSchema
from apps.folders.db.schemas import FolderAppletSchema
from apps.schedule.db.schemas import EventSchema, UserEventsSchema
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.db.schemas.user_applet_access import UserPinSchema
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import (
    RespondentAppletAccess,
    UserAppletAccess,
)
from apps.workspaces.domain.workspace import (
    AppletRoles,
    WorkspaceManager,
    WorkspaceRespondent,
)
from apps.workspaces.errors import (
    AppletAccessDenied,
    UserAppletAccessesNotFound,
)
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserAppletAccessCRUD"]


class _UserAppletFilter(Filtering):
    owner_id = FilterField(UserAppletAccessSchema.owner_id)
    roles = FilterField(UserAppletAccessSchema.role, lookup=Comparisons.IN)

    def prepare_roles(self, value: str):
        return value.split(",")


class _UserAppletOrdering(Ordering):
    created_at = AppletSchema.created_at
    display_name = AppletSchema.display_name


class _UserAppletSearch(Searching):
    search_fields = [AppletSchema.display_name]


class _AppletUsersFilter(Filtering):
    role = FilterField(UserAppletAccessSchema.role)


class _WorkspaceRespondentOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name
    is_pinned = Ordering.Clause(literal_column("is_pinned"))
    secret_ids = Ordering.Clause(literal_column("secret_ids"))
    nicknames = Ordering.Clause(literal_column("nicknames"))
    created_at = Ordering.Clause(func.min(UserAppletAccessSchema.created_at))
    last_seen = Ordering.Clause(
        func.coalesce(UserSchema.last_seen_at, UserSchema.created_at)
    )


class _AppletRespondentOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name
    is_pinned = Ordering.Clause(literal_column("is_pinned"))
    secret_id = Ordering.Clause(literal_column("secret_id"))
    nickname = Ordering.Clause(literal_column("nickname"))
    created_at = Ordering.Clause(UserAppletAccessSchema.created_at)
    last_seen = Ordering.Clause(
        func.coalesce(UserSchema.last_seen_at, UserSchema.created_at)
    )


class _WorkspaceRespondentSearch(Searching):
    search_fields = [
        func.array_agg(UserAppletAccessSchema.meta["nickname"].astext),
        func.array_agg(UserAppletAccessSchema.meta["secretUserId"].astext),
    ]


class _AppletRespondentSearch(Searching):
    search_fields = [
        UserAppletAccessSchema.meta["nickname"].astext,
        UserAppletAccessSchema.meta["secretUserId"].astext,
    ]


class _AppletManagersOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name
    last_name = UserSchema.last_name
    created_at = UserSchema.created_at
    is_pinned = Ordering.Clause(literal_column("is_pinned"))
    roles = Ordering.Clause(literal_column("roles"))


class _AppletUsersSearch(Searching):
    search_fields = [
        UserSchema.first_name,
        UserSchema.last_name,
        UserSchema.email,
    ]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_accessible_applets(
        self,
        user_id: uuid.UUID,
        query_params: QueryParams,
        folder_applet_query: Query,
        folder_id: uuid.UUID | None,
    ) -> list[AppletSchema]:
        if folder_id:
            is_pinned_var = func.coalesce(
                FolderAppletSchema.pinned_at, func.now()
            )
            query: Query = select(
                AppletSchema,
                case(
                    (FolderAppletSchema.pinned_at != None, true()),  # noqa
                    else_=false(),
                ),
            )
            query = query.where(AppletSchema.id.in_(folder_applet_query))
            query = query.join(
                FolderAppletSchema,
                and_(
                    FolderAppletSchema.applet_id == AppletSchema.id,
                    FolderAppletSchema.folder_id == folder_id,
                ),
                isouter=True,
            )
            query = query.order_by(is_pinned_var.desc())
            query = query.group_by(
                AppletSchema.id,
                AppletSchema.display_name,
                AppletSchema.created_at,
                FolderAppletSchema.pinned_at,
            )
        else:
            query = select(AppletSchema, false())
            query = query.where(AppletSchema.id.notin_(folder_applet_query))
            query = query.group_by(
                AppletSchema.id,
                AppletSchema.display_name,
                AppletSchema.created_at,
            )

        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(AppletSchema.soft_exists())

        if query_params.filters:
            query = query.where(
                *_UserAppletFilter().get_clauses(**query_params.filters)
            )
        if query_params.ordering:
            query = query.order_by(
                *_UserAppletOrdering().get_clauses(*query_params.ordering)
            )
        if query_params.search:
            query = query.where(
                _UserAppletSearch().get_clauses(query_params.search)
            )
        query = paging(query, query_params.page, query_params.limit)
        db_result = await self._execute(query)

        applets = []
        for applet_schema, is_pinned in db_result.all():
            applet_schema.is_pinned = is_pinned
            applets.append(applet_schema)
        return applets

    async def get_accessible_applets_count(
        self,
        user_id: uuid.UUID,
        query_params: QueryParams,
        folder_applet_query: Query,
        folder_id: uuid.UUID | None,
    ) -> int:
        applet_ids: Query = select(AppletSchema.id)
        applet_ids = applet_ids.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        applet_ids = applet_ids.where(UserAppletAccessSchema.soft_exists())
        applet_ids = applet_ids.where(
            UserAppletAccessSchema.user_id == user_id
        )
        applet_ids = applet_ids.where(AppletSchema.soft_exists())
        if folder_id:
            applet_ids = applet_ids.where(
                AppletSchema.id.in_(folder_applet_query)
            )
        else:
            applet_ids = applet_ids.where(
                AppletSchema.id.notin_(folder_applet_query)
            )
        applet_ids = applet_ids.group_by(
            AppletSchema.id,
            AppletSchema.display_name,
            AppletSchema.created_at,
        )

        if query_params.filters:
            applet_ids = applet_ids.where(
                *_UserAppletFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            applet_ids = applet_ids.where(
                _UserAppletSearch().get_clauses(query_params.search)
            )

        query: Query = select(count(AppletSchema.id))
        query = query.where(AppletSchema.id.in_(applet_ids))

        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def get_applet_role_by_user_id(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().first()

    def user_applet_ids_query(self, user_id: uuid.UUID) -> Query:
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(
                [Role.OWNER, Role.MANAGER, Role.EDITOR]
            )
        )
        return query

    async def get_applet_owner(
        self, applet_id: uuid.UUID
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == Role.OWNER)
        db_result = await self._execute(query)
        try:
            return db_result.scalars().one()
        except NoResultFound:
            raise AppletAccessDenied()

    async def get_by_id(self, id_: uuid.UUID) -> UserAppletAccess:
        """Fetch UserAppletAccess by id from the database."""

        # Get UserAppletAccess from the database
        if not (instance := await self._get("id", id_)):
            raise UserAppletAccessesNotFound(id_=id_)

        # Get internal model
        user_applet_access: UserAppletAccess = UserAppletAccess.from_orm(
            instance
        )

        return user_applet_access

    async def get_by_user_id_for_managers(
        self, user_id_: uuid.UUID
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).where(
            self.schema_class.user_id == user_id_,
            self.schema_class.soft_exists(),
            exists().where(
                AppletSchema.id == self.schema_class.applet_id,
                AppletSchema.soft_exists(),
            ),
        )
        query = query.where(
            self.schema_class.role.in_(
                [
                    Role.OWNER,
                    Role.MANAGER,
                    Role.COORDINATOR,
                    Role.EDITOR,
                    Role.REVIEWER,
                ]
            )
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def save(
        self, schema: UserAppletAccessSchema
    ) -> UserAppletAccessSchema:
        """Return UserAppletAccess instance and the created information."""
        return await self._create(schema)

    async def create_many(
        self, schemas: list[UserAppletAccessSchema]
    ) -> list[UserAppletAccessSchema]:
        return await self._create_many(schemas)

    async def upsert_user_applet_access(self, schema: UserAppletAccessSchema):
        values = {
            "invitor_id": schema.invitor_id,
            "owner_id": schema.owner_id,
            "user_id": schema.user_id,
            "applet_id": schema.applet_id,
            "role": schema.role,
            "is_deleted": schema.is_deleted,
            "meta": schema.meta,
        }
        stmt = insert(UserAppletAccessSchema).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                UserAppletAccessSchema.user_id,
                UserAppletAccessSchema.applet_id,
                UserAppletAccessSchema.role,
            ],
            set_={
                "invitor_id": schema.invitor_id,
                "owner_id": schema.owner_id,
                "user_id": stmt.excluded.user_id,
                "applet_id": stmt.excluded.applet_id,
                "role": stmt.excluded.role,
                "is_deleted": stmt.excluded.is_deleted,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "meta": stmt.excluded.meta,
            },
        )

        await self._execute(stmt)

    async def upsert_user_applet_access_list(
        self, schemas: list[UserAppletAccessSchema]
    ):
        values_list = [
            {
                "invitor_id": schema.invitor_id,
                "owner_id": schema.owner_id,
                "user_id": schema.user_id,
                "applet_id": schema.applet_id,
                "role": schema.role,
                "is_deleted": schema.is_deleted,
                "meta": schema.meta,
            }
            for schema in schemas
        ]

        stmt = insert(UserAppletAccessSchema).values(values_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                UserAppletAccessSchema.user_id,
                UserAppletAccessSchema.applet_id,
                UserAppletAccessSchema.role,
            ],
            set_={
                "user_id": stmt.excluded.user_id,
                "applet_id": stmt.excluded.applet_id,
                "role": stmt.excluded.role,
                "is_deleted": stmt.excluded.is_deleted,
                "meta": stmt.excluded.meta,
            },
        )

        await self._execute(stmt)

        return await self.get_user_applet_access_list(schemas)

    async def get_user_applet_access_list(
        self, schemas: list[UserAppletAccessSchema]
    ):
        user_ids = [schema.user_id for schema in schemas]
        applet_ids = [schema.applet_id for schema in schemas]
        roles = [schema.role for schema in schemas]

        query = select(UserAppletAccessSchema).where(
            (UserAppletAccessSchema.user_id.in_(user_ids))
            & (UserAppletAccessSchema.applet_id.in_(applet_ids))
            & (UserAppletAccessSchema.role.in_(roles))
        )

        result = await self._execute(query)
        return result.fetchall()

    async def get(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, role: str
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)

        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def get_by_roles(
        self,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        ordered_roles: list[str],
    ) -> UserAppletAccessSchema | None:
        """
        Get first role by order
        """

        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(ordered_roles))
        query = query.order_by(
            func.array_position(ordered_roles, UserAppletAccessSchema.role)
        )

        result = await self._execute(query)
        return result.scalars().first() or None

    # Get by applet id and user id and role respondent
    async def get_by_applet_and_user_as_respondent(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        result = await self._execute(query)
        return result.scalars().first()

    async def get_user_roles_to_applet(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_roles_in_roles(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, roles: list[str]
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_secret_user_id_for_applet(
        self,
        applet_id: uuid.UUID,
        secret_user_id: str,
        exclude_id: uuid.UUID | None = None,
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        if exclude_id:
            query = query.where(UserAppletAccessSchema.id != exclude_id)
        query = query.where(
            UserAppletAccessSchema.meta.op("->>")("secretUserId")
            == secret_user_id
        )
        db_result = await self._execute(query)

        return db_result.scalars().first()

    async def get_user_id_applet_and_role(
        self, applet_id: uuid.UUID, role: Role
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.user_id))
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def delete_all_by_applet_id(self, applet_id: uuid.UUID):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def get_workspace_respondents(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceRespondent], int]:
        schedule_exists = (
            select(UserEventsSchema)
            .join(EventSchema, EventSchema.id == UserEventsSchema.event_id)
            .where(
                UserEventsSchema.user_id == UserAppletAccessSchema.user_id,
                EventSchema.applet_id == UserAppletAccessSchema.applet_id,
            )
            .exists()
            .correlate(UserAppletAccessSchema)
        )

        is_pinned = (
            exists()
            .where(
                UserPinSchema.user_id == user_id,
                UserPinSchema.pinned_user_id == UserSchema.id,
                UserPinSchema.owner_id == owner_id,
                UserPinSchema.role == UserPinRole.respondent,
            )
            .correlate(UserSchema)
        )

        assigned_respondents = select(
            literal_column("val").cast(UUID)
        ).select_from(
            func.jsonb_array_elements_text(
                case(
                    (
                        func.jsonb_typeof(
                            UserAppletAccessSchema.meta[text("'respondents'")]
                        )
                        == text("'array'"),
                        UserAppletAccessSchema.meta[text("'respondents'")],
                    ),
                    else_=text("'[]'::jsonb"),
                )
            ).alias("val")
        )

        has_access = (
            exists()
            .where(
                UserAppletAccessSchema.applet_id == AppletSchema.id,
                UserAppletAccessSchema.user_id == user_id,
                UserAppletAccessSchema.soft_exists(),
                or_(
                    UserAppletAccessSchema.role.in_(
                        [Role.OWNER, Role.MANAGER, Role.COORDINATOR]
                    ),
                    and_(
                        UserAppletAccessSchema.role == Role.REVIEWER,
                        UserSchema.id == any_(assigned_respondents),
                    ),
                ),
            )
            .correlate(AppletSchema, UserSchema)
        )

        field_nickname = UserAppletAccessSchema.respondent_nickname
        field_secret_user_id = UserAppletAccessSchema.respondent_secret_id

        query: Query = (
            select(
                # fmt: off
                UserSchema.id,
                UserSchema.first_name,
                UserSchema.last_name,
                UserSchema.is_anonymous_respondent,

                func.coalesce(
                    UserSchema.last_seen_at, UserSchema.created_at
                ).label("last_seen"),

                func.array_agg(
                    aggregate_order_by(
                        func.distinct(field_nickname), field_nickname
                    )
                ).label("nicknames"),

                func.array_agg(
                    aggregate_order_by(
                        func.distinct(field_secret_user_id),
                        field_secret_user_id,
                    )
                ).label("secret_ids"),

                is_pinned.label("is_pinned"),

                func.array_agg(
                    func.json_build_object(
                        text("'applet_id'"), AppletSchema.id,
                        text("'applet_display_name'"),
                        AppletSchema.display_name,  # noqa: E501
                        text("'applet_image'"), AppletSchema.image,
                        text("'access_id'"), UserAppletAccessSchema.id,
                        text("'respondent_nickname'"), field_nickname,
                        text("'respondent_secret_id'"), field_secret_user_id,
                        text("'has_individual_schedule'"), schedule_exists,
                        text("'encryption'"), AppletSchema.encryption,
                    )
                ).label("details"),
            )
            .select_from(UserAppletAccessSchema)
            .join(
                AppletSchema,
                and_(
                    AppletSchema.id == UserAppletAccessSchema.applet_id,
                    AppletSchema.soft_exists(),
                ),
            )
            .join(
                UserSchema,
                UserSchema.id == UserAppletAccessSchema.user_id,
            )
            .where(
                UserAppletAccessSchema.owner_id == owner_id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
                has_access,
                UserAppletAccessSchema.applet_id == applet_id
                if applet_id
                else True,
                UserAppletAccessSchema.soft_exists(),
            )
            .group_by(UserSchema.id)
        )

        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.having(
                _WorkspaceRespondentSearch().get_clauses(query_params.search)
            )

        coro_total = self._execute(
            select(count()).select_from(query.with_only_columns(UserSchema.id))
        )

        if query_params.ordering:
            query = query.order_by(
                *_WorkspaceRespondentOrdering().get_clauses(
                    *query_params.ordering
                )
            )
        query = paging(query, query_params.page, query_params.limit)

        coro_data = self._execute(query)

        res_data, res_total = await asyncio.gather(coro_data, coro_total)

        data = parse_obj_as(list[WorkspaceRespondent], res_data.all())
        total = res_total.scalar()

        return data, total

    async def get_workspace_managers(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceManager], int]:
        is_pinned = (
            exists()
            .where(
                UserPinSchema.user_id == user_id,
                UserPinSchema.pinned_user_id == UserSchema.id,
                UserPinSchema.owner_id == owner_id,
                UserPinSchema.role == UserPinRole.manager,
            )
            .correlate(UserSchema)
        )

        has_access = (
            exists()
            .where(
                UserAppletAccessSchema.soft_exists(),
                UserAppletAccessSchema.user_id == user_id,
                UserAppletAccessSchema.applet_id == AppletSchema.id,
                UserAppletAccessSchema.role.in_([Role.OWNER, Role.MANAGER]),
            )
            .correlate(AppletSchema)
        )

        query: Query = (
            select(
                # fmt: off
                UserSchema.id,
                UserSchema.first_name,
                UserSchema.last_name,
                UserSchema.email,

                func.coalesce(
                    UserSchema.last_seen_at, UserSchema.created_at
                ).label("last_seen"),

                is_pinned.label("is_pinned"),

                func.array_agg(
                    aggregate_order_by(
                        func.distinct(UserAppletAccessSchema.role),
                        UserAppletAccessSchema.role
                    )
                ).label("roles"),

                func.array_agg(
                    aggregate_order_by(
                        func.json_build_object(
                            text("'applet_id'"), AppletSchema.id,
                            text("'applet_display_name'"),
                            AppletSchema.display_name,  # noqa: E501
                            text("'applet_image'"), AppletSchema.image,
                            text("'access_id'"), UserAppletAccessSchema.id,
                            text("'role'"), UserAppletAccessSchema.role,
                            text("'encryption'"), AppletSchema.encryption,
                            text("'reviewer_respondents'"), UserAppletAccessSchema.reviewer_respondents,  # noqa: E501
                        ),
                        AppletSchema.id
                    )
                ).label("applets"),
            )
            .select_from(UserAppletAccessSchema)
            .join(
                AppletSchema,
                and_(
                    AppletSchema.id == UserAppletAccessSchema.applet_id,
                    AppletSchema.soft_exists(),
                ),
            )
            .join(
                UserSchema,
                UserSchema.id == UserAppletAccessSchema.user_id,
            )
            .where(
                UserAppletAccessSchema.soft_exists(),
                UserAppletAccessSchema.owner_id == owner_id,
                UserAppletAccessSchema.role != Role.RESPONDENT,
                has_access,
                UserAppletAccessSchema.applet_id == applet_id
                if applet_id
                else True,
            )
            .group_by(UserSchema.id)
        )

        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )

        coro_total = self._execute(
            select(count()).select_from(query.with_only_columns(UserSchema.id))
        )

        if query_params.ordering:
            query = query.order_by(
                *_AppletManagersOrdering().get_clauses(*query_params.ordering)
            )
        query = paging(query, query_params.page, query_params.limit)

        coro_data = self._execute(query)

        res_data, res_total = await asyncio.gather(coro_data, coro_total)

        data = parse_obj_as(list[WorkspaceManager], res_data.all())
        total = res_total.scalar()

        if query_params.search:
            data_search = []
            total_search = 0
            for manager in data:
                if manager.plain_first_name:
                    first_name_lower = manager.plain_first_name.lower()
                else:
                    first_name_lower = ""
                if manager.plain_last_name:
                    last_name_lower = manager.plain_last_name.lower()
                else:
                    last_name_lower = ""
                if (
                    query_params.search.lower() in first_name_lower
                    or query_params.search.lower() in last_name_lower
                ):
                    data_search.append(manager)
                    total_search += 1
            return data_search, total_search

        return data, total

    async def get_all_by_user_id_and_roles(
        self, user_id_: uuid.UUID, roles: list[Role]
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.soft_exists(),
            self.schema_class.user_id == user_id_,
            self.schema_class.role.in_(roles),
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_user_applet_accesses_by_roles(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
        roles: list[Role],
        invitor_id: uuid.UUID | None = None,
    ) -> list[UserAppletAccessSchema]:
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.soft_exists())
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.applet_id.in_(applet_ids))
        query = query.where(self.schema_class.role.in_(roles))
        if invitor_id:
            query = query.where(self.schema_class.invitor_id == invitor_id)

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_user_applet_accesses(
        self,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        role: Role,
    ) -> UserAppletAccessSchema:
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.soft_exists())
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.applet_id == applet_id)
        query = query.where(self.schema_class.role == role)

        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def remove_access_by_user_and_applet_to_role(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
        roles: list[Role],
    ):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.where(UserAppletAccessSchema.applet_id.in_(applet_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def check_access_by_user_and_owner(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        roles: list[Role] | None = None,
    ) -> bool:
        query: Query = select(self.schema_class.id)
        query = query.where(self.schema_class.soft_exists())
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.owner_id == owner_id)
        if roles:
            query = query.where(self.schema_class.role.in_(roles))
        query = query.limit(1)

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def pin(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        pinned_user_id: uuid.UUID,
        pin_role: UserPinRole,
    ):
        query = select(UserPinSchema).where(
            UserPinSchema.user_id == user_id,
            UserPinSchema.owner_id == owner_id,
            UserPinSchema.pinned_user_id == pinned_user_id,
            UserPinSchema.role == pin_role,
        )
        res = await self._execute(query)
        if user_pin := res.scalar():
            await self.session.delete(user_pin)
        else:
            user_pin = UserPinSchema(
                user_id=user_id,
                owner_id=owner_id,
                pinned_user_id=pinned_user_id,
                role=pin_role,
            )
            await self._create(user_pin)

    async def unpin(self, id_: uuid.UUID):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.id == id_)
        query = query.values(pinned_at=None)

        await self._execute(query)

    async def get_applet_users_by_roles(
        self, applet_id: uuid.UUID, roles: list[Role]
    ) -> list[uuid.UUID]:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        db_result = await self._execute(query)

        results = db_result.scalars().all()
        return [r.user_id for r in results]

    async def has_managers(self, user_id: uuid.UUID) -> bool:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.owner_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(
                [Role.MANAGER, Role.COORDINATOR, Role.EDITOR, Role.REVIEWER]
            )
        )
        query = query.limit(1)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def has_access(
        self, user_id: uuid.UUID, owner_id: uuid.UUID, roles: list[Role]
    ) -> bool:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.limit(1)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def get_respondent_accesses_by_owner_id(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> list[RespondentAppletAccess]:
        individual_event_query: Query = select(UserEventsSchema.id)
        individual_event_query = individual_event_query.join(
            EventSchema, EventSchema.id == UserEventsSchema.event_id
        )
        individual_event_query = individual_event_query.where(
            UserEventsSchema.user_id == UserAppletAccessSchema.user_id
        )
        individual_event_query = individual_event_query.where(
            EventSchema.applet_id == UserAppletAccessSchema.applet_id
        )

        query: Query = select(
            UserAppletAccessSchema.meta,
            AppletSchema.id,
            AppletSchema.display_name,
            AppletSchema.image,
            exists(individual_event_query),
            AppletSchema.encryption,
        )
        query = query.join(
            AppletSchema, AppletSchema.id == UserAppletAccessSchema.applet_id
        )
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.user_id == respondent_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = paging(query, page, limit)

        db_result = await self._execute(query)

        accesses = []
        results = db_result.all()
        for (
            meta,
            applet_id,
            display_name,
            image,
            has_individual,
            encryption,
        ) in results:
            accesses.append(
                RespondentAppletAccess(
                    applet_id=applet_id,
                    applet_name=display_name,
                    applet_image=image,
                    secret_user_id=meta.get("secretUserId", ""),
                    nickname=meta.get("nickname", ""),
                    has_individual_schedule=has_individual,
                    encryption=encryption,
                )
            )

        return accesses

    async def get_respondent_accesses_by_owner_id_count(
        self,
        owner_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> int:
        query: Query = select(
            count(UserAppletAccessSchema.id),
        )
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.user_id == respondent_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def delete_user_roles(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, roles: list[Role]
    ):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def has_role(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> bool:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == role)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def get_applets_roles_by_priority(
        self, applet_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> dict[uuid.UUID, Role]:
        from_query: Query = select(UserAppletAccessSchema)
        from_query = from_query.where(UserAppletAccessSchema.soft_exists())
        from_query = from_query.where(
            UserAppletAccessSchema.user_id == user_id
        )
        from_query = from_query.where(
            UserAppletAccessSchema.applet_id.in_(applet_ids)
        )
        from_query = from_query.order_by(
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc()
        ).alias("prioritized_access")

        query = select(from_query.c.applet_id, from_query.c.role)
        query = query.distinct(from_query.c.applet_id)

        db_result = await self._execute(query)

        return dict(db_result.all())

    async def get_applets_roles_by_priority_for_workspace(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
    ) -> str | None:
        from_query: Query = select(UserAppletAccessSchema.role)
        from_query = from_query.where(UserAppletAccessSchema.soft_exists())
        from_query = from_query.where(
            UserAppletAccessSchema.owner_id == owner_id
        )
        from_query = from_query.where(
            UserAppletAccessSchema.user_id == user_id
        )
        if applet_ids:
            from_query = from_query.where(
                UserAppletAccessSchema.applet_id.in_(applet_ids)
            )
        from_query = from_query.order_by(
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
        from_query = from_query.limit(1)
        from_query = from_query.alias("prioritized_access")

        query = select(from_query.c.role)
        query = query.distinct(from_query.c.role)

        db_result = await self._execute(query)

        return db_result.scalars().first()

    async def remove_manager_accesses_by_user_id_in_workspace(
        self, owner_id: uuid.UUID, user_id: uuid.UUID
    ):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(
                [Role.MANAGER, Role.COORDINATOR, Role.EDITOR, Role.REVIEWER]
            )
        )
        query = query.values(is_deleted=True)

        await self._execute(query)

    async def update_meta_by_access_id(self, access_id: uuid.UUID, meta: dict):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.id == access_id)
        query = query.values(meta=meta)

        await self._execute(query)

    async def get_workspace_applet_roles(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID] | None = None,
    ) -> list[AppletRoles]:
        ordered_roles = [
            Role.OWNER,
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
            Role.REVIEWER,
            Role.RESPONDENT,
        ]
        query: Query = select(
            UserAppletAccessSchema.applet_id,
            func.array_agg(
                aggregate_order_by(
                    UserAppletAccessSchema.role,
                    func.array_position(
                        ordered_roles, UserAppletAccessSchema.role
                    ),
                )
            ).label("roles"),
        ).where(
            UserAppletAccessSchema.soft_exists(),
            UserAppletAccessSchema.owner_id == owner_id,
            UserAppletAccessSchema.user_id == user_id,
        )
        if applet_ids:
            query = query.where(
                UserAppletAccessSchema.applet_id == any_(applet_ids)
            )

        query = query.group_by(UserAppletAccessSchema.applet_id).order_by(
            UserAppletAccessSchema.applet_id
        )

        result = await self._execute(query)
        data = result.all()

        return parse_obj_as(list[AppletRoles], data)

    async def get_responsible_persons(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        query: Query = select(UserAppletAccessSchema.user_id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        if respondent_id:
            query = query.where(
                or_(
                    UserAppletAccessSchema.role == Role.OWNER,
                    UserAppletAccessSchema.role == Role.MANAGER,
                    and_(
                        UserAppletAccessSchema.role == Role.COORDINATOR,
                        UserAppletAccessSchema.meta.contains(
                            dict(respondents=[str(respondent_id)])
                        ),
                    ),
                )
            )
        else:
            query = query.where(
                or_(
                    UserAppletAccessSchema.role == Role.OWNER,
                    UserAppletAccessSchema.role == Role.MANAGER,
                )
            )
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_user_nickname(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> str | None:
        query: Query = select(UserAppletAccessSchema.meta)
        query = query.where(
            UserAppletAccessSchema.applet_id == applet_id,
            UserAppletAccessSchema.user_id == user_id,
            UserAppletAccessSchema.role == Role.RESPONDENT,
        )
        db_result = await self._execute(query)
        db_result = db_result.first()
        return db_result[0].get("nickname") if db_result else None
