import uuid

from sqlalchemy import (
    and_,
    case,
    delete,
    distinct,
    exists,
    func,
    select,
    update,
)
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.applets.db.schemas import AppletSchema
from apps.schedule.db.schemas import EventSchema, UserEventsSchema
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import (
    RespondentAppletAccess,
    UserAppletAccess,
)
from apps.workspaces.domain.workspace import (
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


class _AppletRespondentsOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name
    pinned = UserAppletAccessSchema.is_pinned
    created_at = UserAppletAccessSchema.created_at


class _AppletRespondentSearch(Searching):
    search_fields = [
        UserAppletAccessSchema.meta["nickname"].astext,
        UserAppletAccessSchema.meta["secretUserId"].astext,
    ]


class _AppletManagersOrdering(Ordering):
    email = UserSchema.email
    first_name = UserSchema.first_name
    created_at = UserSchema.created_at


class _AppletUsersSearch(Searching):
    search_fields = [
        UserSchema.first_name,
        UserSchema.last_name,
        UserSchema.email,
    ]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def get_accesses_by_user_id_in_workspace(
        self, user_id: uuid.UUID, owner_id: uuid.UUID, roles=None
    ) -> list[UserAppletAccess]:
        if roles is None:
            roles = Role.as_list()
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))

        db_result = await self._execute(query)
        return db_result.scalars().all()

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
            AppletSchema.id,
            AppletSchema.display_name,
            AppletSchema.created_at,
            AppletSchema.folder_id,
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
        applet_ids: Query = select(AppletSchema.id)
        applet_ids = applet_ids.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        applet_ids = applet_ids.where(
            UserAppletAccessSchema.user_id == user_id
        )
        applet_ids = applet_ids.where(
            AppletSchema.is_deleted == False  # noqa: E712
        )
        applet_ids = applet_ids.group_by(
            AppletSchema.id,
            AppletSchema.display_name,
            AppletSchema.created_at,
            AppletSchema.folder_id,
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
                [Role.OWNER, Role.MANAGER, Role.EDITOR]
            )
        )
        return query

    async def get_applet_owner(
        self, applet_id: uuid.UUID
    ) -> UserAppletAccessSchema:
        query: Query = select(UserAppletAccessSchema)
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
        self,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        ordered_roles: list[str],
    ) -> UserAppletAccessSchema | None:
        """
        Get first role by order
        """

        query: Query = select(UserAppletAccessSchema)
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

    async def get_workspace_respondents(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> list[WorkspaceRespondent]:
        schedule_query: Query = select(
            UserEventsSchema.user_id,
            EventSchema.applet_id,
        )
        schedule_query = schedule_query.join(
            EventSchema, EventSchema.id == UserEventsSchema.event_id
        )
        schedule_query = schedule_query.distinct().alias("schedules")

        query: Query = select(
            UserSchema,
            UserAppletAccessSchema,
            case(
                (schedule_query.c.user_id != None, True),  # noqa: E711
                else_=False,
            ).label("individual_schedule"),
        )
        query = query.join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.user_id == UserSchema.id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            ),
        )
        query = query.join(
            schedule_query,
            and_(
                schedule_query.c.user_id == UserAppletAccessSchema.user_id,
                schedule_query.c.applet_id == UserAppletAccessSchema.applet_id,
            ),
            isouter=True,
        )
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletRespondentSearch().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_AppletRespondentsOrdering().get_clauses(
                    *query_params.ordering
                )
            )
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)

        users = []
        results = db_result.all()
        for (
            user_schema,
            access,
            has_individual_schedule,
        ) in results:  # type: UserSchema, UserAppletAccess, bool
            users.append(
                WorkspaceRespondent(
                    id=user_schema.id,
                    access_id=access.id,
                    nickname=access.meta.get("nickname"),
                    role=access.role,
                    secret_id=access.meta.get("secretUserId"),
                    last_seen=user_schema.last_seen_at
                    or user_schema.created_at,
                    has_individual_schedule=has_individual_schedule,
                    is_pinned=access.is_pinned,
                )
            )
        return users

    async def get_workspace_respondents_count(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> int:
        query: Query = select(count(UserSchema.id))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletRespondentSearch().get_clauses(query_params.search)
            )
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def get_workspace_managers(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> list[WorkspaceManager]:
        query: Query = select(
            UserSchema,
            func.string_agg(UserAppletAccessSchema.role, "|").label("roles"),
        )
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role != Role.RESPONDENT)
        query = query.group_by(UserSchema.id)
        if query_params.filters:
            query = query.where(
                *_AppletUsersFilter().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _AppletUsersSearch().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_AppletManagersOrdering().get_clauses(*query_params.ordering)
            )
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)

        users = []
        results = db_result.all()
        for user_schema, roles in results:  # type:UserSchema, str
            users.append(
                WorkspaceManager(
                    id=user_schema.id,
                    first_name=user_schema.first_name,
                    last_name=user_schema.last_name,
                    email=user_schema.email,
                    roles=list(set(roles.split("|"))),
                    last_seen=user_schema.last_seen_at
                    or user_schema.created_at,
                )
            )
        return users

    async def get_workspace_managers_count(
        self, owner_id: uuid.UUID, query_params: QueryParams
    ) -> int:
        query: Query = select(count(distinct(UserSchema.id)))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.user_id == UserSchema.id,
        )
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.role != Role.RESPONDENT)
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

    async def get_user_applet_accesses_by_roles(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
        roles: list[Role],
        invitor_id: uuid.UUID | None = None,
    ) -> list[UserAppletAccessSchema]:
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.applet_id.in_(applet_ids))
        query = query.where(self.schema_class.role.in_(roles))
        if invitor_id:
            query = query.where(self.schema_class.invitor_id == invitor_id)

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def remove_access_by_user_and_applet_to_role(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
        roles: list[Role],
    ):
        query: Query = delete(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.where(UserAppletAccessSchema.applet_id.in_(applet_ids))
        await self._execute(query)

    async def check_access_by_user_and_owner(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        roles: list[Role] | None = None,
    ) -> bool:
        query: Query = select(self.schema_class.id)
        query = query.where(self.schema_class.user_id == user_id)
        query = query.where(self.schema_class.owner_id == owner_id)
        if roles:
            query = query.where(self.schema_class.role.in_(roles))
        query = query.limit(1)

        db_result = await self._execute(query)

        return db_result.scalars().first() is not None

    async def pin(self, id_: uuid.UUID):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.id == id_)
        query = query.values(
            is_pinned=case(
                (
                    UserAppletAccessSchema.is_pinned == False,  # noqa: E712
                    True,
                ),
                else_=False,
            )
        )

        await self._execute(query)

    async def unpin(self, id_: uuid.UUID):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.id == id_)
        query = query.values(pinned_at=None)

        await self._execute(query)

    async def get_applet_users_by_roles(
        self, applet_id: uuid.UUID, roles: list[Role]
    ) -> list[uuid.UUID]:
        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        db_result = await self._execute(query)

        results = db_result.scalars().all()
        return [r.user_id for r in results]

    async def has_managers(self, user_id: uuid.UUID) -> bool:
        query: Query = select(UserAppletAccessSchema)
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
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.user_id == respondent_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

    async def delete_user_roles(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, roles: list[Role]
    ):
        query: Query = delete(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        await self._execute(query)

    async def has_role(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> bool:
        query: Query = select(UserAppletAccessSchema)
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
