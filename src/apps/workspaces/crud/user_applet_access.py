import uuid

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.applets.db.schemas import AppletSchema
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    UserAppletAccess,
    UserAppletAccessItem,
)
from apps.workspaces.domain.workspace import WorkspaceUser
from apps.workspaces.errors import (
    AppletAccessDenied,
    UserAppletAccessesNotFound,
)
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserAppletAccessCRUD"]


class _UserAppletFilter(Filtering):
    owner_id = FilterField(UserAppletAccessSchema.owner_id)
    folder_id = FilterField(AppletSchema.folder_id)
    roles = FilterField(UserAppletAccessSchema.role, lookup="in")

    def prepare_roles(self, value: str):
        return value.split(",")


class _UserAppletOrdering(Ordering):
    created_at = AppletSchema.created_at
    display_name = AppletSchema.display_name


class _UserAppletSearch(Searching):
    search_fields = [AppletSchema.display_name]


class _AppletUsersFilter(Filtering):
    owner_id = FilterField(UserAppletAccessSchema.owner_id)
    applet_id = FilterField(UserAppletAccessSchema.applet_id)
    role = FilterField(UserAppletAccessSchema.role)


class _AppletUsersOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name


class _AppletUsersSearch(Searching):
    search_fields = [UserSchema.first_name, UserSchema.last_name]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_accessible_applets(
        self, user_id: uuid.UUID, query_params: QueryParams
    ) -> list[AppletSchema]:
        query: Query = select(AppletSchema)
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        query = query.group_by(
            AppletSchema.id, AppletSchema.display_name, AppletSchema.created_at
        )

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
        for applet_schema in db_result.scalars().all():
            applets.append(applet_schema)
        return applets

    async def get_accessible_applets_count(
        self, user_id: uuid.UUID, query_params: QueryParams
    ) -> int:
        query: Query = select(count(AppletSchema.id))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(AppletSchema.is_deleted == False)  # noqa: E712
        query = query.group_by(
            AppletSchema.id, AppletSchema.display_name, AppletSchema.created_at
        )

        if query_params.filters:
            query = query.where(
                *_UserAppletFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _UserAppletSearch().get_clauses(query_params.search)
            )
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def get_applet_role_by_user_id(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().first()

    def user_applet_ids_query(self, user_id: uuid.UUID) -> Query:
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(
                [Role.ADMIN, Role.MANAGER, Role.EDITOR]
            )
        )
        return query

    async def get_applet_owner(
        self, applet_id: uuid.UUID
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == Role.ADMIN)
        db_result = await self._execute(query)
        try:
            return db_result.scalars().one()
        except NoResultFound:
            raise AppletAccessDenied()

    async def get_by_id(self, id_: int) -> UserAppletAccess:
        """Fetch UserAppletAccess by id from the database."""

        # Get UserAppletAccess from the database
        if not (instance := await self._get("id", id_)):
            raise UserAppletAccessesNotFound(id_=id_)

        # Get internal model
        user_applet_access: UserAppletAccess = UserAppletAccess.from_orm(
            instance
        )

        return user_applet_access

    async def get_by_user_id(
        self, user_id_: uuid.UUID
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).where(
            self.schema_class.user_id == user_id_
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def get_by_user_applet_role(
        self,
        schema: UserAppletAccessItem,
    ) -> UserAppletAccess | None:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == schema.user_id,
            self.schema_class.applet_id == schema.applet_id,
            self.schema_class.role == schema.role,
        )
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

    async def save(
        self, schema: UserAppletAccessSchema
    ) -> UserAppletAccessSchema:
        """Return UserAppletAccess instance and the created information."""
        return await self._create(schema)

    async def get(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, role: str
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)

        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def get_by_roles(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, roles: list[str]
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))

        result = await self._execute(query)
        return result.scalars().one_or_none()

    # Get by applet id and user id and role respondent
    async def get_by_applet_and_user_as_respondent(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        result = await self._execute(query)
        return result.scalars().first()

    async def get_user_roles_to_applet(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_roles_in_roles(
        self, user_id: uuid.UUID, applet_id: uuid.UUID, roles: list[str]
    ) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_secret_user_id_for_applet(
        self, applet_id: uuid.UUID, secret_user_id: str
    ) -> UserAppletAccessSchema | None:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
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
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == role)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def delete_all_by_applet_id(self, applet_id: uuid.UUID):
        query: Query = delete(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        await self._execute(query)

    async def get_workspace_users(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> list[WorkspaceUser]:
        query: Query = select(
            UserSchema,
            func.string_agg(
                UserAppletAccessSchema.meta.op("->>")("nickname"), "," ""
            ).label("nicknames"),
            func.string_agg(
                UserAppletAccessSchema.meta.op("->>")("secretUserId"), "," ""
            ).label("secret_ids"),
            func.string_agg(UserAppletAccessSchema.role, "," "").label(
                "roles"
            ),
        )
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        query = query.group_by(UserSchema.id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletUsersSearch().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.where(
                *_AppletUsersOrdering().get_clauses(*query_params.ordering)
            )
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)

        users = []
        results = db_result.all()
        for user_schema, nicknames, secret_ids, roles in results:
            users.append(
                WorkspaceUser(
                    id=user_schema.id,
                    nickname=nicknames[0] if nicknames else None,
                    roles=roles.split(","),
                    secret_id=secret_ids[0] if secret_ids else None,
                    last_seen=user_schema.last_seen_at
                    or user_schema.created_at,
                )
            )
        return users

    async def get_workspace_users_count(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> int:
        query: Query = select(count(distinct(UserSchema.id)))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletUsersSearch().get_clauses(query_params.search)
            )
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def get_all_by_user_id_and_roles(
        self, user_id_: uuid.UUID, roles: list[Role]
    ) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_,
            self.schema_class.role.in_(roles),
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [
            UserAppletAccess.from_orm(user_applet_access)
            for user_applet_access in results
        ]

    async def delete_all_by_user_and_applet(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ):
        query: Query = delete(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        await self._execute(query)

    async def check_access_by_user_and_owner(
        self, user_id: uuid.UUID, owner_id: uuid.UUID
    ) -> bool:
        query: Query = select(self.schema_class.id)
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.owner_id == owner_id)
        query = query.limit(1)

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None
