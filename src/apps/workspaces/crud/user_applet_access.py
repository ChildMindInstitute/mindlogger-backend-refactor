import uuid
from datetime import datetime
from typing import Tuple

from asyncpg.exceptions import UniqueViolationError
from pydantic import parse_obj_as
from sqlalchemy import (
    Unicode,
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
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID, aggregate_order_by, insert
from sqlalchemy.engine import Result
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count
from sqlalchemy_utils import StringEncryptedType

from apps.applets.db.schemas import AppletSchema
from apps.invitations.constants import InvitationStatus
from apps.invitations.db import InvitationSchema
from apps.schedule.db.schemas import EventSchema, UserEventsSchema
from apps.shared.encryption import get_key
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.subjects.constants import SubjectStatus
from apps.subjects.db.schemas import SubjectSchema
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.db.schemas.user_applet_access import UserPinSchema
from apps.workspaces.domain.constants import Role, UserPinRole
from apps.workspaces.domain.user_applet_access import RespondentAppletAccess, UserAppletAccess
from apps.workspaces.domain.workspace import AppletRoles, WorkspaceManager, WorkspaceRespondent
from apps.workspaces.errors import AppletAccessDenied, UserAppletAccessesNotFound
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserAppletAccessCRUD"]


class _AppletUsersFilter(Filtering):
    role = FilterField(UserAppletAccessSchema.role)
    shell = FilterField(UserSchema.id, method_name="null")
    user_id = FilterField(UserSchema.id)
    respondent_secret_id = FilterField(SubjectSchema.secret_user_id)


class _AppletInvitationFilter(Filtering):
    role = FilterField(InvitationSchema.role)
    shell = FilterField(InvitationSchema.user_id, method_name="null")
    user_id = FilterField(InvitationSchema.user_id)


class _WorkspaceRespondentOrdering(Ordering):
    is_pinned = Ordering.Clause(literal_column("is_pinned"))
    secret_ids = Ordering.Clause(literal_column("secret_ids"))
    tags = Ordering.Clause(literal_column("tags_order"))
    created_at = Ordering.Clause(func.min(UserAppletAccessSchema.created_at))
    status = Ordering.Clause(literal_column("status_order"))
    # TODO: https://mindlogger.atlassian.net/browse/M2-6834
    # Add support to order by last_seen

    encrypted_fields = {
        "nicknames": Ordering.Clause(
            func.array_remove(
                func.array_agg(func.distinct(func.decrypt_internal(SubjectSchema.nickname, get_key()))),
                None,
            )
        )
    }


class _WorkspaceRespondentSearch(Searching):
    search_fields = [
        func.array_agg(SubjectSchema.nickname),
        func.array_agg(SubjectSchema.secret_user_id),
    ]


class _AppletRespondentSearch(Searching):
    search_fields = [
        UserAppletAccessSchema.meta["secretUserId"].astext,
    ]


class _AppletUsersSearch(Searching):
    search_fields = [
        UserSchema.first_name,
        UserSchema.last_name,
        UserSchema.email,
    ]


class UserAppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

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

    async def get_applet_role_by_user_id_exist(
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
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_([Role.OWNER, Role.MANAGER, Role.EDITOR]))
        return query

    async def get_applet_owner(self, applet_id: uuid.UUID) -> UserAppletAccessSchema:
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
        user_applet_access: UserAppletAccess = UserAppletAccess.from_orm(instance)

        return user_applet_access

    async def get_by_user_id_for_managers(self, user_id_: uuid.UUID) -> list[UserAppletAccess]:
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

        return [UserAppletAccess.from_orm(user_applet_access) for user_applet_access in results]

    async def save(self, schema: UserAppletAccessSchema) -> UserAppletAccessSchema:
        """Return UserAppletAccess instance and the created information."""
        return await self._create(schema)

    async def create_many(self, schemas: list[UserAppletAccessSchema]) -> list[UserAppletAccessSchema]:
        return await self._create_many(schemas)

    async def upsert_user_applet_access(self, schema: UserAppletAccessSchema, where=None):
        values = {
            "invitor_id": schema.invitor_id,
            "owner_id": schema.owner_id,
            "user_id": schema.user_id,
            "applet_id": schema.applet_id,
            "role": schema.role,
            "is_deleted": schema.is_deleted,
            "meta": schema.meta,
            "nickname": schema.nickname,
            "title": schema.title,
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
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "meta": stmt.excluded.meta,
                "nickname": stmt.excluded.nickname,
                "title": stmt.excluded.title,
            },
            where=where,
        ).returning(UserAppletAccessSchema)

        result = list(await self._execute(stmt))
        if not result:
            raise UniqueViolationError("duplicate key value violates unique" ' constraint "unique_user_applet_role"')

        return result

    async def upsert_user_applet_access_list(self, schemas: list[UserAppletAccessSchema]):
        values_list = [
            {
                "invitor_id": schema.invitor_id,
                "owner_id": schema.owner_id,
                "user_id": schema.user_id,
                "applet_id": schema.applet_id,
                "role": schema.role,
                "is_deleted": schema.is_deleted,
                "meta": schema.meta,
                "nickname": schema.nickname,
                "title": schema.title,
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
                "invitor_id": stmt.excluded.invitor_id,
                "owner_id": stmt.excluded.owner_id,
                "user_id": stmt.excluded.user_id,
                "applet_id": stmt.excluded.applet_id,
                "role": stmt.excluded.role,
                "is_deleted": stmt.excluded.is_deleted,
                "meta": stmt.excluded.meta,
                "nickname": stmt.excluded.nickname,
                "title": stmt.excluded.title,
            },
        )

        await self._execute(stmt)

        return await self.get_user_applet_access_list(schemas)

    async def get_user_applet_access_list(self, schemas: list[UserAppletAccessSchema]):
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

    async def get(self, user_id: uuid.UUID, applet_id: uuid.UUID, role: str) -> UserAppletAccessSchema | None:
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
        ordered_roles: list[Role],
    ) -> UserAppletAccessSchema | None:
        """
        Get first role by order
        """

        query: Query = select(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(ordered_roles))
        query = query.order_by(func.array_position(ordered_roles, UserAppletAccessSchema.role))

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

    async def get_user_roles_to_applet(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> list[str]:
        query: Query = select(distinct(UserAppletAccessSchema.role))
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
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
        query = query.where(UserAppletAccessSchema.meta.op("->>")("secretUserId") == secret_user_id)
        db_result = await self._execute(query)

        return db_result.scalars().first()

    async def get_user_id_applet_and_role(self, applet_id: uuid.UUID, role: Role) -> list[str]:
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

    @staticmethod
    def workspace_applets_subquery(owner_id: uuid.UUID, applet_id: uuid.UUID | None) -> Query:
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        if applet_id:
            query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        return query.subquery()

    async def get_workspace_respondents(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceRespondent], int, list[str]]:
        field_nickname = SubjectSchema.nickname
        field_secret_user_id = SubjectSchema.secret_user_id
        workspace_applets_sq = self.workspace_applets_subquery(owner_id, applet_id)

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
                UserPinSchema.owner_id == owner_id,
                UserPinSchema.role == UserPinRole.respondent,
                or_(
                    and_(UserPinSchema.pinned_subject_id.is_(None), UserPinSchema.pinned_user_id == UserSchema.id),
                    and_(
                        UserPinSchema.pinned_user_id.is_(None),
                        UserPinSchema.pinned_subject_id == any_(func.array_agg(SubjectSchema.id)),
                    ),
                ),
            )
            .correlate(UserSchema, SubjectSchema)
        )

        assigned_subjects = select(literal_column("val").cast(UUID)).select_from(
            func.jsonb_array_elements_text(
                case(
                    (
                        func.jsonb_typeof(UserAppletAccessSchema.meta[text("'subjects'")]) == text("'array'"),
                        UserAppletAccessSchema.meta[text("'subjects'")],
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
                    UserAppletAccessSchema.role.in_([Role.OWNER, Role.MANAGER, Role.COORDINATOR]),
                    and_(
                        UserAppletAccessSchema.role == Role.REVIEWER,
                        SubjectSchema.id == any_(assigned_subjects.scalar_subquery()),
                    ),
                ),
            )
            .correlate(AppletSchema, SubjectSchema)
        )

        status_invited = UserSchema.id.isnot(None)
        status_pending = (
            select(InvitationSchema.id)
            .where(
                InvitationSchema.status == InvitationStatus.PENDING,
                InvitationSchema.applet_id.in_(select(workspace_applets_sq)),
                InvitationSchema.meta.has_key("subject_id"),
                func.cast(InvitationSchema.meta["subject_id"].astext, UUID(as_uuid=True))
                == any_(func.array_agg(SubjectSchema.id)),
            )
            .exists()
        )

        query: Query = select(
            # fmt: off
            UserSchema.id,
            case(
                (UserSchema.id.is_(None), func.array_agg(SubjectSchema.email)[1]), else_=UserSchema.email_encrypted
            ).label("email"),
            case((UserSchema.id.isnot(None), UserSchema.is_anonymous_respondent), else_=false()).label(
                "is_anonymous_respondent"
            ),
            case(
                (status_invited, SubjectStatus.INVITED),
                (status_pending, SubjectStatus.PENDING),
                else_=SubjectStatus.NOT_INVITED,
            ).label("status"),
            # Add special ordering for status column (used only in order_by)
            case(
                (status_pending, 0),  # Pending full accounts
                (status_invited, 1),  # Full accounts
                else_=2,  # Limited accounts
            ).label("status_order"),
            func.array_agg(SubjectSchema.id).label("subjects"),
            # Add tag column for ordering
            func.array_agg(SubjectSchema.tag).label("tags_order"),
            is_pinned.label("is_pinned"),
            func.array_remove(func.array_agg(func.distinct(field_nickname)), None)
            .cast(ARRAY(StringEncryptedType(Unicode, get_key)))
            .label("nicknames"),
            func.array_agg(
                aggregate_order_by(
                    func.distinct(field_secret_user_id),
                    field_secret_user_id,
                )
            ).label("secret_ids"),
            func.array_agg(
                func.json_build_object(
                    text("'applet_id'"),
                    AppletSchema.id,
                    text("'applet_display_name'"),
                    AppletSchema.display_name,  # noqa: E501
                    text("'applet_image'"),
                    AppletSchema.image,
                    text("'access_id'"),
                    UserAppletAccessSchema.id,
                    text("'respondent_nickname'"),
                    field_nickname,
                    text("'respondent_secret_id'"),
                    field_secret_user_id,
                    text("'has_individual_schedule'"),
                    schedule_exists,
                    text("'encryption'"),
                    AppletSchema.encryption,
                    text("'subject_id'"),
                    SubjectSchema.id,
                    text("'subject_tag'"),
                    SubjectSchema.tag,
                    text("'subject_first_name'"),
                    SubjectSchema.first_name,
                    text("'subject_last_name'"),
                    SubjectSchema.last_name,
                    text("'subject_created_at'"),
                    SubjectSchema.created_at,
                )
            ).label("details"),
        )
        query = query.select_from(SubjectSchema)
        query = query.join(UserSchema, UserSchema.id == SubjectSchema.user_id, isouter=True)

        query = query.join(AppletSchema, AppletSchema.id == SubjectSchema.applet_id)
        query = query.join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.applet_id == SubjectSchema.applet_id,
                UserAppletAccessSchema.user_id == SubjectSchema.user_id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            ),
            isouter=True,
        )

        query = query.where(
            has_access,
            SubjectSchema.applet_id.in_(select(workspace_applets_sq)),
            SubjectSchema.applet_id == applet_id if applet_id else True,
            SubjectSchema.soft_exists(),
        )

        query = query.group_by(
            UserSchema.id,
            func.coalesce(UserSchema.id, func.gen_random_uuid()),
        )

        if query_params.filters:
            query = query.where(*_AppletUsersFilter().get_clauses(**query_params.filters))
        if query_params.search:
            query = query.having(_WorkspaceRespondentSearch().get_clauses(query_params.search))

        # Get total count before ordering to evaluate eligibility for ordering by encrypted fields
        coro_total = self._execute(select(count()).select_from(query.with_only_columns(UserSchema.id).subquery()))
        total = (await coro_total).scalar()

        ordering = _WorkspaceRespondentOrdering()

        if query_params.ordering:
            query = query.order_by(*ordering.get_clauses(*query_params.ordering, count=total))

        query = paging(query, query_params.page, query_params.limit)

        data = (await self._execute(query)).all()
        data = parse_obj_as(list[WorkspaceRespondent], data)
        ordering_fields = ordering.get_ordering_fields(total)

        return data, total, ordering_fields

    async def get_applet_respondents_total(self, applet_id: uuid.UUID) -> int:
        query: Query = (
            select(count(SubjectSchema.id))
            .select_from(SubjectSchema)
            .where(
                SubjectSchema.applet_id == applet_id,
            )
        )

        result = await self._execute(query)
        return result.scalar()

    async def get_workspace_managers(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceManager], int, list[str]]:
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

        invited_users_query = (
            select(
                InvitationSchema.id,
                InvitationSchema.first_name,
                InvitationSchema.last_name,
                InvitationSchema.email,
                func.array_agg(
                    aggregate_order_by(
                        func.distinct(InvitationSchema.title),
                        InvitationSchema.title,
                    )
                ).label("titles"),
                func.array_agg(
                    aggregate_order_by(
                        func.distinct(InvitationSchema.role),
                        InvitationSchema.role,
                    )
                ).label("roles"),
                func.array_agg(
                    aggregate_order_by(
                        func.json_build_object(
                            text("'applet_id'"),
                            AppletSchema.id,
                            text("'applet_display_name'"),
                            AppletSchema.display_name,  # noqa: E501
                            text("'applet_image'"),
                            AppletSchema.image,
                            text("'role'"),
                            InvitationSchema.role,
                            text("'encryption'"),
                            AppletSchema.encryption,
                        ),
                        AppletSchema.id,
                    )
                ).label("applets"),
                InvitationSchema.status,
                InvitationSchema.created_at,
                InvitationSchema.user_id,
                InvitationSchema.key,
            )
            .select_from(InvitationSchema)
            .join(
                AppletSchema,
                and_(
                    AppletSchema.id == InvitationSchema.applet_id,
                    AppletSchema.soft_exists(),
                ),
            )
            .where(
                InvitationSchema.role != Role.RESPONDENT,
                InvitationSchema.status == InvitationStatus.PENDING,
                InvitationSchema.applet_id == applet_id,
                has_access,
            )
            .group_by(InvitationSchema.id)
        )

        accepted_users_query = (
            select(
                # fmt: off
                UserSchema.id,
                UserSchema.first_name,
                UserSchema.last_name,
                UserSchema.email_encrypted,
                UserSchema.created_at,
                func.coalesce(UserSchema.last_seen_at, UserSchema.created_at).label("last_seen"),
                func.array_agg(
                    aggregate_order_by(
                        func.distinct(UserAppletAccessSchema.title),
                        UserAppletAccessSchema.title,
                    )
                ).label("titles"),
                func.array_agg(
                    aggregate_order_by(
                        func.distinct(UserAppletAccessSchema.role),
                        UserAppletAccessSchema.role,
                    )
                ).label("roles"),
                func.array_agg(
                    aggregate_order_by(
                        func.json_build_object(
                            text("'applet_id'"),
                            AppletSchema.id,
                            text("'applet_display_name'"),
                            AppletSchema.display_name,  # noqa: E501
                            text("'applet_image'"),
                            AppletSchema.image,
                            text("'access_id'"),
                            UserAppletAccessSchema.id,
                            text("'role'"),
                            UserAppletAccessSchema.role,
                            text("'encryption'"),
                            AppletSchema.encryption,
                            text("'reviewer_subjects'"),
                            UserAppletAccessSchema.reviewer_subjects,  # noqa: E501
                        ),
                        AppletSchema.id,
                    )
                ).label("applets"),
                is_pinned.label("is_pinned"),
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
                has_access,
                UserAppletAccessSchema.role != Role.RESPONDENT,
                UserAppletAccessSchema.applet_id == applet_id if applet_id else True,
            )
            .group_by(UserSchema.id)
        )

        if query_params.filters:
            invited_users_query = invited_users_query.where(
                *_AppletInvitationFilter().get_clauses(**query_params.filters)
            )
            accepted_users_query = accepted_users_query.where(*_AppletUsersFilter().get_clauses(**query_params.filters))

        invited_users = invited_users_query.cte("invited_users")
        accepted_users = accepted_users_query.cte("accepted_users")

        query: Query = (
            select(
                func.coalesce(accepted_users.c.id, invited_users.c.id).label("id"),
                func.coalesce(accepted_users.c.first_name, invited_users.c.first_name).label("first_name"),
                func.coalesce(accepted_users.c.last_name, invited_users.c.last_name).label("last_name"),
                func.coalesce(accepted_users.c.email_encrypted, invited_users.c.email).label("email_encrypted"),
                func.coalesce(accepted_users.c.created_at, invited_users.c.created_at).label("created_at"),
                func.coalesce(accepted_users.c.last_seen, invited_users.c.created_at).label("last_seen"),
                func.coalesce(accepted_users.c.roles, invited_users.c.roles).label("roles"),
                func.coalesce(accepted_users.c.applets, invited_users.c.applets, []).label("applets"),
                func.coalesce(accepted_users.c.titles, invited_users.c.titles, [])
                .cast(ARRAY(StringEncryptedType(Unicode, get_key)))
                .label("titles"),
                func.coalesce(invited_users.c.status, InvitationStatus.APPROVED).label("status"),
                func.coalesce(accepted_users.c.is_pinned, False).label("is_pinned"),
                invited_users.c.key.label("invitation_key"),
            )
            .select_from(invited_users)
            .join(accepted_users, accepted_users.c.id == invited_users.c.user_id, isouter=True, full=True)
        )

        # Get total count before ordering to evaluate eligibility for ordering by encrypted fields
        coro_total = self._execute(
            select(count()).select_from(query.with_only_columns(literal_column("status")).subquery())
        )
        total = (await coro_total).scalar()

        class _AppletManagersOrdering(Ordering):
            created_at = Ordering.Clause(literal_column("created_at"))
            is_pinned = Ordering.Clause(literal_column("is_pinned"))
            last_seen = Ordering.Clause(literal_column("last_seen"))
            roles = Ordering.Clause(literal_column("roles"))
            status = Ordering.Clause(literal_column("status"))

            encrypted_fields = {
                "email": Ordering.Clause(
                    func.decrypt_internal(
                        func.coalesce(accepted_users.c.email_encrypted, invited_users.c.email), get_key()
                    )
                ),
                "first_name": Ordering.Clause(
                    func.decrypt_internal(
                        func.coalesce(accepted_users.c.first_name, invited_users.c.first_name), get_key()
                    )
                ),
                "last_name": Ordering.Clause(
                    func.decrypt_internal(
                        func.coalesce(accepted_users.c.last_name, invited_users.c.last_name), get_key()
                    )
                ),
            }

        ordering = _AppletManagersOrdering()

        if query_params.ordering:
            query = query.order_by(*ordering.get_clauses(*query_params.ordering, count=total))

        query = paging(query, query_params.page, query_params.limit)

        data = (await self._execute(query)).all()
        data = parse_obj_as(list[WorkspaceManager], data)
        ordering_fields = ordering.get_ordering_fields(total)

        # TODO: Fix via class Searching
        #  using database fields - StringEncryptedType
        if query_params.search:
            data_search = []
            total_search = 0
            for manager in data:
                if manager.first_name:
                    first_name_lower = manager.first_name.lower()
                else:
                    first_name_lower = ""
                if manager.last_name:
                    last_name_lower = manager.last_name.lower()
                else:
                    last_name_lower = ""
                if manager.email_encrypted:
                    email_encrypted_lower = manager.email_encrypted.lower()
                else:
                    email_encrypted_lower = ""

                if (
                    query_params.search.lower() in first_name_lower
                    or query_params.search.lower() in last_name_lower
                    or query_params.search.lower() in email_encrypted_lower
                ):
                    data_search.append(manager)
                    total_search += 1
            return data_search, total_search, ordering_fields

        return data, total, ordering_fields

    async def get_all_by_user_id_and_roles(self, user_id_: uuid.UUID, roles: list[Role]) -> list[UserAppletAccess]:
        query: Query = select(self.schema_class).filter(
            self.schema_class.soft_exists(),
            self.schema_class.user_id == user_id_,
            self.schema_class.role.in_(roles),
        )
        result: Result = await self._execute(query)
        results: list[UserAppletAccessSchema] = result.scalars().all()

        return [UserAppletAccess.from_orm(user_applet_access) for user_applet_access in results]

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

    async def check_access_by_subject_and_owner(
        self, subject_id: uuid.UUID, owner_id: uuid.UUID, roles: list[Role] | None
    ):
        query: Query = select(UserAppletAccessSchema)
        query = query.join(SubjectSchema, SubjectSchema.applet_id == UserAppletAccessSchema.applet_id)
        query = query.where(
            UserAppletAccessSchema.owner_id == owner_id,
            UserAppletAccessSchema.role.in_(roles),
            SubjectSchema.id == subject_id,
        )
        query = query.limit(1)
        db_result = await self._execute(query)
        return db_result.scalars().first() is not None

    async def pin(
        self,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        pin_role: UserPinRole,
        pinned_user_id: uuid.UUID | None,
        pinned_subject_id: uuid.UUID | None,
        force_unpin: bool = False,
    ):
        query = select(UserPinSchema).where(
            UserPinSchema.user_id == user_id,
            UserPinSchema.owner_id == owner_id,
            UserPinSchema.role == pin_role,
        )
        if pinned_user_id:
            query = query.where(UserPinSchema.pinned_user_id == pinned_user_id)
        else:
            query = query.where(UserPinSchema.pinned_subject_id == pinned_subject_id)

        res = await self._execute(query)
        if user_pin := res.scalar():
            await self.session.delete(user_pin)
        elif force_unpin is False:
            user_pin = UserPinSchema(
                user_id=user_id,
                owner_id=owner_id,
                pinned_user_id=pinned_user_id,
                pinned_subject_id=pinned_subject_id,
                role=pin_role,
            )
            await self._create(user_pin)

    async def get_applet_users_by_roles(self, applet_id: uuid.UUID, roles: list[Role]) -> list[uuid.UUID]:
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
            UserAppletAccessSchema.role.in_([Role.MANAGER, Role.COORDINATOR, Role.EDITOR, Role.REVIEWER])
        )
        query = query.limit(1)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def has_access(self, user_id: uuid.UUID, owner_id: uuid.UUID, roles: list[Role]) -> bool:
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
        individual_event_query = individual_event_query.join(EventSchema, EventSchema.id == UserEventsSchema.event_id)
        individual_event_query = individual_event_query.where(
            UserEventsSchema.user_id == UserAppletAccessSchema.user_id
        )
        individual_event_query = individual_event_query.where(EventSchema.applet_id == UserAppletAccessSchema.applet_id)

        query: Query = select(
            SubjectSchema.secret_user_id,
            SubjectSchema.nickname,
            AppletSchema.id,
            AppletSchema.display_name,
            AppletSchema.image,
            exists(individual_event_query),
            AppletSchema.encryption,
        )
        query = query.select_from(UserAppletAccessSchema)
        query = query.join(AppletSchema, AppletSchema.id == UserAppletAccessSchema.applet_id)
        query = query.join(
            SubjectSchema,
            and_(
                SubjectSchema.applet_id == UserAppletAccessSchema.applet_id,
                SubjectSchema.user_id == UserAppletAccessSchema.user_id,
            ),
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
            secret_user_id,
            nickname,
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
                    secret_user_id=secret_user_id,
                    nickname=nickname,
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

    async def delete_user_roles(self, applet_id: uuid.UUID, user_id: uuid.UUID, roles: list[Role]):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def has_role(self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role) -> bool:
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
        from_query = from_query.where(UserAppletAccessSchema.user_id == user_id)
        from_query = from_query.where(UserAppletAccessSchema.applet_id.in_(applet_ids))
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
        from_query = from_query.where(UserAppletAccessSchema.owner_id == owner_id)
        from_query = from_query.where(UserAppletAccessSchema.user_id == user_id)
        if applet_ids:
            from_query = from_query.where(UserAppletAccessSchema.applet_id.in_(applet_ids))
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

    async def update_meta_by_access_id(self, access_id: uuid.UUID, meta: dict, nickname: str):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.id == access_id)
        query = query.values(meta=meta, nickname=nickname)

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
                    func.array_position(ordered_roles, UserAppletAccessSchema.role),
                )
            ).label("roles"),
        ).where(
            UserAppletAccessSchema.soft_exists(),
            UserAppletAccessSchema.owner_id == owner_id,
            UserAppletAccessSchema.user_id == user_id,
        )
        if applet_ids:
            query = query.where(UserAppletAccessSchema.applet_id == any_(applet_ids))

        query = query.group_by(UserAppletAccessSchema.applet_id).order_by(UserAppletAccessSchema.applet_id)

        result = await self._execute(query)
        data = result.all()

        return parse_obj_as(list[AppletRoles], data)

    async def get_responsible_persons(self, applet_id: uuid.UUID, subject_id: uuid.UUID | None) -> list[UserSchema]:
        query: Query = select(UserSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.join(
            UserAppletAccessSchema,
            UserSchema.id == UserAppletAccessSchema.user_id,
        )
        if subject_id:
            query = query.where(
                or_(
                    UserAppletAccessSchema.role == Role.OWNER,
                    UserAppletAccessSchema.role == Role.MANAGER,
                    and_(
                        UserAppletAccessSchema.role == Role.REVIEWER,
                        UserAppletAccessSchema.meta.contains(dict(subjects=[str(subject_id)])),
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

    async def get_respondent_by_applet_and_owner(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> tuple[str, str, uuid.UUID] | None:
        query: Query = select(SubjectSchema.nickname, SubjectSchema.secret_user_id, SubjectSchema.id)
        query = query.select_from(UserAppletAccessSchema)
        query = query.where(
            UserAppletAccessSchema.owner_id == owner_id,
            UserAppletAccessSchema.applet_id == applet_id,
            UserAppletAccessSchema.user_id == respondent_id,
            UserAppletAccessSchema.role == Role.RESPONDENT,
            UserAppletAccessSchema.soft_exists(),
        )
        query = query.join(
            SubjectSchema,
            and_(
                SubjectSchema.user_id == UserAppletAccessSchema.user_id,
                SubjectSchema.applet_id == UserAppletAccessSchema.applet_id,
            ),
        )
        db_result = await self._execute(query)
        db_result = db_result.all()  # noqa
        return db_result[0] if db_result else None

    async def get_management_applets(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        query: Query = select(UserAppletAccessSchema.applet_id)
        query = query.where(
            UserAppletAccessSchema.applet_id.in_(applet_ids),
            UserAppletAccessSchema.user_id == user_id,
            UserAppletAccessSchema.role.in_(Role.managers()),
            UserAppletAccessSchema.soft_exists(),
        )
        db_result = await self._execute(query)
        db_result = db_result.scalars().all()  # noqa
        return db_result

    async def change_owner_of_applet_accesses(self, new_owner: uuid.UUID, applet_id: uuid.UUID):
        query: Query = update(UserAppletAccessSchema)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.values(owner_id=new_owner)
        await self._execute(query)

    async def change_subject_pins_to_user(self, user_id: uuid.UUID, subject_id: uuid.UUID):
        query: Query = update(UserPinSchema)
        query = query.where(UserPinSchema.role == UserPinRole.respondent, UserPinSchema.pinned_subject_id == subject_id)
        query = query.values(pinned_subject_id=None, pinned_user_id=user_id)  # noqa
        await self._execute(query)

    async def get_workspace_pins(self, owner_id: uuid.UUID) -> list[UserPinSchema]:
        query: Query = select(UserPinSchema)
        query = query.where(UserPinSchema.owner_id == owner_id)
        db_res = await self._execute(query)
        return db_res.scalars().all()
