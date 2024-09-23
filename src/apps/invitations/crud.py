import uuid
from typing import Any

from sqlalchemy import and_, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import Role
from apps.invitations.constants import InvitationStatus
from apps.invitations.db import InvitationSchema
from apps.invitations.domain import (
    InvitationDetail,
    InvitationDetailBase,
    InvitationDetailGeneric,
    InvitationDetailRespondent,
    InvitationDetailReviewer,
    InvitationRespondent,
)
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.subjects.db.schemas import SubjectSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from infrastructure.database import BaseCRUD

__all__ = ["InvitationCRUD"]


class _InvitationFiltering(Filtering):
    applet_id = FilterField(InvitationSchema.applet_id)
    invitor_id = FilterField(InvitationSchema.invitor_id)
    role = FilterField(InvitationSchema.role)


class _InvitationSearching(Searching):
    search_fields = [InvitationSchema.applet_id]


class _InvitationOrdering(Ordering):
    id = InvitationSchema.id
    applet_id = InvitationSchema.applet_id
    created_at = InvitationSchema.created_at
    updated_at = InvitationSchema.updated_at


class InvitationCRUD(BaseCRUD[InvitationSchema]):
    schema_class = InvitationSchema

    async def save(self, schema: InvitationSchema) -> InvitationSchema:
        schema = await self._create(schema)
        return schema

    async def update(self, lookup: str, value: Any, schema: InvitationSchema) -> InvitationSchema:
        schema = await self._update_one(lookup, value, schema)
        return schema

    async def get_pending_by_invitor_id(self, user_id: uuid.UUID, query_params: QueryParams) -> list[InvitationDetail]:
        """Return the list of pending invitations
        for the user who is invitor.
        """

        user_applet_ids: Query = select(UserAppletAccessSchema.applet_id)
        user_applet_ids = user_applet_ids.where(UserAppletAccessSchema.user_id == user_id)
        user_applet_ids = user_applet_ids.where(
            UserAppletAccessSchema.role.in_(
                [
                    Role.OWNER,
                    Role.MANAGER,
                    Role.EDITOR,
                    Role.REVIEWER,
                    Role.COORDINATOR,
                ]
            )
        )

        query: Query = select(
            InvitationSchema,
            AppletSchema.display_name.label("applet_name"),
            SubjectSchema.secret_user_id.label("user_secret_id"),
            SubjectSchema.nickname.label("nickname"),
            SubjectSchema.first_name.label("first_name"),
            SubjectSchema.last_name.label("last_name"),
        )
        query = query.where(InvitationSchema.applet_id.in_(user_applet_ids))
        query = query.join(AppletSchema, AppletSchema.id == InvitationSchema.applet_id)

        query = query.outerjoin(
            SubjectSchema,
            and_(
                InvitationSchema.meta.has_key("subject_id"),
                SubjectSchema.id == func.cast(InvitationSchema.meta["subject_id"].astext, UUID(as_uuid=True)),
            ),
        )

        query = query.where(InvitationSchema.status == InvitationStatus.PENDING)
        if query_params.filters:
            query = query.where(*_InvitationFiltering().get_clauses(**query_params.filters))
        if query_params.search:
            query = query.where(_InvitationSearching().get_clauses(query_params.search))
        if query_params.ordering:
            query = query.order_by(*_InvitationOrdering().get_clauses(*query_params.ordering))
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)
        results = []
        for invitation, applet_name, secret_id, nickname, first_name, last_name in db_result.all():
            results.append(
                InvitationDetail(
                    id=invitation.id,
                    email=invitation.email,
                    applet_id=invitation.applet_id,
                    applet_name=applet_name,
                    role=invitation.role,
                    key=invitation.key,
                    status=invitation.status,
                    invitor_id=invitation.invitor_id,
                    meta=invitation.meta,
                    first_name=first_name if invitation.role == Role.RESPONDENT else invitation.first_name,
                    last_name=last_name if invitation.role == Role.RESPONDENT else invitation.last_name,
                    created_at=invitation.created_at,
                    nickname=nickname,
                    secret_user_id=secret_id,
                    tag=invitation.tag,
                )
            )
        return results

    async def get_latest_by_emails(self, emails: list[str]) -> dict[str, InvitationDetail]:
        """Return the list of "latest invitation" for the provided emails"""
        query: Query = select(
            InvitationSchema,
            AppletSchema.display_name.label("applet_name"),
            SubjectSchema.secret_user_id.label("user_secret_id"),
            SubjectSchema.nickname.label("nickname"),
            SubjectSchema.first_name.label("first_name"),
            SubjectSchema.last_name.label("last_name"),
        )
        query = query.join(AppletSchema, AppletSchema.id == InvitationSchema.applet_id)
        query = query.outerjoin(
            SubjectSchema,
            and_(
                InvitationSchema.meta.has_key("subject_id"),
                SubjectSchema.id == func.cast(InvitationSchema.meta["subject_id"].astext, UUID(as_uuid=True)),
            ),
        )
        query = query.where(InvitationSchema.email.in_(emails))
        query = query.where(InvitationSchema.status.in_([InvitationStatus.PENDING, InvitationStatus.APPROVED]))
        db_result = await self._execute(query)
        results = {}
        for invitation, applet_name, secret_id, nickname, first_name, last_name in db_result.all():
            results[f"{invitation.email}_{invitation.applet_id}"] = InvitationDetail(
                id=invitation.id,
                email=invitation.email,
                applet_id=invitation.applet_id,
                applet_name=applet_name,
                role=invitation.role,
                key=invitation.key,
                status=invitation.status,
                invitor_id=invitation.invitor_id,
                meta=invitation.meta,
                first_name=first_name if invitation.role == Role.RESPONDENT else invitation.first_name,
                last_name=last_name if invitation.role == Role.RESPONDENT else invitation.last_name,
                created_at=invitation.created_at,
                nickname=nickname,
                secret_user_id=secret_id,
                tag=invitation.tag,
            )
        return results

    async def get_pending_by_invitor_id_count(self, user_id: uuid.UUID, query_params: QueryParams) -> int:
        """Return the cont of pending invitations
        for the user who is invitor.
        """
        user_applet_ids: Query = select(UserAppletAccessSchema.applet_id)
        user_applet_ids = user_applet_ids.where(UserAppletAccessSchema.user_id == user_id)
        user_applet_ids = user_applet_ids.where(
            UserAppletAccessSchema.role.in_(
                [
                    Role.OWNER,
                    Role.MANAGER,
                    Role.EDITOR,
                    Role.REVIEWER,
                    Role.COORDINATOR,
                ]
            )
        )

        query: Query = select(count(InvitationSchema.id))
        query = query.where(InvitationSchema.applet_id.in_(user_applet_ids))
        query = query.where(InvitationSchema.status == InvitationStatus.PENDING)
        if query_params.filters:
            query = query.where(*_InvitationFiltering().get_clauses(**query_params.filters))
        if query_params.search:
            query = query.where(_InvitationSearching().get_clauses(query_params.search))

        result = await self._execute(query)

        return result.scalars().first() or 0

    async def get_by_email_and_key(self, email: str, key: uuid.UUID) -> InvitationDetailGeneric | None:
        """Return the specific invitation
        for the user who was invited.
        """
        query: Query = select(
            InvitationSchema,
            AppletSchema.display_name.label("applet_name"),
            SubjectSchema.secret_user_id,
            SubjectSchema.nickname,
            SubjectSchema.first_name,
            SubjectSchema.last_name,
        )
        query = query.join(AppletSchema, AppletSchema.id == InvitationSchema.applet_id)
        query = query.outerjoin(
            SubjectSchema,
            and_(
                InvitationSchema.meta.has_key("subject_id"),
                SubjectSchema.id == func.cast(InvitationSchema.meta["subject_id"].astext, UUID(as_uuid=True)),
            ),
        )
        query = query.where(InvitationSchema.email == email)
        query = query.where(InvitationSchema.key == key)
        db_result = await self._execute(query)
        result = db_result.one_or_none()
        if not result:
            return None

        invitation, applet_name, secret_id, nickname, first_name, last_name = result
        invitation_detail_base = InvitationDetailBase(
            id=invitation.id,
            email=invitation.email,
            applet_id=invitation.applet_id,
            applet_name=applet_name,
            role=invitation.role,
            key=invitation.key,
            status=invitation.status,
            invitor_id=invitation.invitor_id,
            first_name=first_name if invitation.role == Role.RESPONDENT else invitation.first_name,
            last_name=last_name if invitation.role == Role.RESPONDENT else invitation.last_name,
            created_at=invitation.created_at,
            user_id=invitation.user_id,
            tag=invitation.tag,
            title=invitation.title,
        )
        if invitation.role == Role.RESPONDENT:
            return InvitationDetailRespondent(
                meta=invitation.meta,
                nickname=nickname,
                secret_user_id=secret_id,
                **invitation_detail_base.dict(),
            )
        elif invitation.role == Role.REVIEWER:
            return InvitationDetailReviewer(
                meta=invitation.meta,
                **invitation_detail_base.dict(),
            )
        else:
            return InvitationDetail(
                meta={},
                **invitation_detail_base.dict(),
            )

    async def get_pending_invitation(self, email: str, applet_id: uuid.UUID) -> InvitationRespondent:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.email == email)
        query = query.where(InvitationSchema.applet_id == applet_id)
        query = query.where(InvitationSchema.status == InvitationStatus.PENDING)
        db_result: Result = await self._execute(query)
        return db_result.scalar_one_or_none()

    async def get_pending_respondent_invitation_by_ids(
        self, applet_id: uuid.UUID, invitation_ids: list[uuid.UUID]
    ) -> list[InvitationRespondent]:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.role == Role.RESPONDENT)
        query = query.where(InvitationSchema.applet_id == applet_id)
        query = query.where(InvitationSchema.status == InvitationStatus.PENDING)
        query = query.where(InvitationSchema.id.in_(invitation_ids))
        db_result: Result = await self._execute(query)
        return db_result.scalars().all()

    async def get_pending_subject_invitation(self, applet_id: uuid.UUID, subject_id: uuid.UUID) -> InvitationRespondent:
        query: Query = select(InvitationSchema).where(
            InvitationSchema.applet_id == applet_id,
            InvitationSchema.status == InvitationStatus.PENDING,
            InvitationSchema.soft_exists(),
            InvitationSchema.subject_id == subject_id,
        )
        db_result: Result = await self._execute(query)
        return db_result.scalar_one_or_none()

    async def approve_by_id(self, id_: uuid.UUID, user_id: uuid.UUID):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.APPROVED, user_id=user_id)

        await self._execute(query)

    async def decline_by_id(self, id_: uuid.UUID, user_id: uuid.UUID):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.DECLINED, user_id=user_id)

        await self._execute(query)

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        query: Query = delete(InvitationSchema)
        query = query.where(InvitationSchema.applet_id == applet_id)
        await self._execute(query)

    async def get_for_respondent(
        self,
        applet_id: uuid.UUID,
        secret_user_id: str,
        status: InvitationStatus,
        invited_email: str = "",
    ) -> InvitationSchema | None:
        schema = self.schema_class
        query: Query = select(schema).where(
            schema.applet_id == applet_id,
            schema.role == Role.RESPONDENT,
            schema.status == status,
            schema.meta[text("'secret_user_id'")].astext == secret_user_id,
        )
        # NOTE: this case is valid only for updating pending invitation.
        # If pending invitation exists with provided secret_user_id, but
        # email is the same as invited email - it is ok because existing
        # invitation will be updated.
        # So need to exclude invited_email from filter.
        if invited_email:
            query = query.where(schema.email != invited_email)
        db_result = await self._execute(query)

        return db_result.scalars().first()

    async def delete_by_applet_ids(
        self,
        email: str | None,
        applet_ids: list[uuid.UUID],
        roles: list[Role],
    ):
        query: Query = delete(InvitationSchema)
        query = query.where(
            InvitationSchema.email == email,
            InvitationSchema.applet_id.in_(applet_ids),
            InvitationSchema.status == InvitationStatus.APPROVED,
            InvitationSchema.role.in_(roles),
            InvitationSchema.soft_exists(),
        )
        await self._execute(query)

    async def get_meta(self, key: uuid.UUID) -> dict | None:
        query: Query = select(InvitationSchema.meta)
        query = query.where(InvitationSchema.key == key)
        result_db = await self._execute(query)
        return result_db.scalar_one_or_none()

    async def get_invited_emails(self, applet_id: uuid.UUID) -> list[str]:
        query: Query = select(InvitationSchema.email)
        query = query.where(
            InvitationSchema.applet_id == applet_id,
            InvitationSchema.status == InvitationStatus.PENDING,
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def delete_by_subject(self, subject_id: uuid.UUID, statuses: list[InvitationStatus] | None = None):
        query: Query = delete(InvitationSchema).where(
            InvitationSchema.role == Role.RESPONDENT, InvitationSchema.subject_id == subject_id
        )
        if statuses:
            query = query.where(InvitationSchema.status.in_(statuses))
        await self._execute(query)
