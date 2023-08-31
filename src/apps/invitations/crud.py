import uuid
from typing import Any

from sqlalchemy import delete, select, text, update
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
    InvitationManagers,
    InvitationRespondent,
    InvitationReviewer,
)
from apps.shared.encryption import decrypt
from apps.shared.filtering import FilterField, Filtering
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import ManagersRole
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

    async def update(
        self, lookup: str, value: Any, schema: InvitationSchema
    ) -> InvitationSchema:
        schema = await self._update_one(lookup, value, schema)
        return schema

    async def get_pending_by_invited_email(
        self, email: str, query_params: QueryParams
    ) -> list[InvitationDetail]:
        """Return the list of pending invitations for the invited user."""

        query: Query = select(
            InvitationSchema, AppletSchema.display_name.label("applet_name")
        )
        query = query.join(
            AppletSchema, AppletSchema.id == InvitationSchema.applet_id
        )
        query = query.where(InvitationSchema.email == email)
        query = query.where(
            InvitationSchema.status == InvitationStatus.PENDING
        )
        if query_params.search:
            query = query.where(
                _InvitationSearching().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_InvitationOrdering().get_clauses(*query_params.ordering)
            )
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)
        results = []
        for invitation, applet_name in db_result.all():
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
                    first_name=invitation.first_name,
                    last_name=invitation.last_name,
                    created_at=invitation.created_at,
                )
            )
        return results

    async def get_pending_by_invited_email_count(
        self, email: str, query_params: QueryParams
    ) -> int:
        """Return the count of pending invitations for the invited user."""

        query: Query = select(count(InvitationSchema.id))
        query = query.where(InvitationSchema.email == email)
        query = query.where(
            InvitationSchema.status == InvitationStatus.PENDING
        )
        if query_params.search:
            query = query.where(
                _InvitationSearching().get_clauses(query_params.search)
            )

        result = await self._execute(query)

        return result.scalars().first() or 0

    async def get_pending_by_invitor_id(
        self, user_id: uuid.UUID, query_params: QueryParams
    ) -> list[InvitationDetail]:
        """Return the list of pending invitations
        for the user who is invitor.
        """

        user_applet_ids: Query = select(UserAppletAccessSchema.applet_id)
        user_applet_ids = user_applet_ids.where(
            UserAppletAccessSchema.user_id == user_id
        )
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
            InvitationSchema, AppletSchema.display_name.label("applet_name")
        )
        query = query.where(InvitationSchema.applet_id.in_(user_applet_ids))
        query = query.join(
            AppletSchema, AppletSchema.id == InvitationSchema.applet_id
        )
        query = query.where(
            InvitationSchema.status == InvitationStatus.PENDING
        )
        if query_params.filters:
            query = query.where(
                *_InvitationFiltering().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _InvitationSearching().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_InvitationOrdering().get_clauses(*query_params.ordering)
            )
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)
        results = []
        for invitation, applet_name in db_result.all():
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
                    first_name=invitation.first_name,
                    last_name=invitation.last_name,
                    created_at=invitation.created_at,
                )
            )
        return results

    async def get_pending_by_invitor_id_count(
        self, user_id: uuid.UUID, query_params: QueryParams
    ) -> int:
        """Return the cont of pending invitations
        for the user who is invitor.
        """
        user_applet_ids: Query = select(UserAppletAccessSchema.applet_id)
        user_applet_ids = user_applet_ids.where(
            UserAppletAccessSchema.user_id == user_id
        )
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
        query = query.where(
            InvitationSchema.status == InvitationStatus.PENDING
        )
        if query_params.filters:
            query = query.where(
                *_InvitationFiltering().get_clauses(**query_params.filters)
            )
        if query_params.search:
            query = query.where(
                _InvitationSearching().get_clauses(query_params.search)
            )

        result = await self._execute(query)

        return result.scalars().first() or 0

    async def get_by_email_and_key(
        self, email: str, key: uuid.UUID
    ) -> InvitationDetailGeneric | None:
        """Return the specific invitation
        for the user who was invited.
        """
        query: Query = select(
            InvitationSchema, AppletSchema.display_name.label("applet_name")
        )
        query = query.join(
            AppletSchema, AppletSchema.id == InvitationSchema.applet_id
        )
        query = query.where(InvitationSchema.email == email)
        query = query.where(InvitationSchema.key == key)
        db_result = await self._execute(query)
        result = db_result.one_or_none()
        if not result:
            return None
        invitation, applet_name = result
        first_name = decrypt(bytes.fromhex(invitation.first_name)).decode(
            "utf-8"
        )
        last_name = decrypt(bytes.fromhex(invitation.last_name)).decode(
            "utf-8"
        )
        invitation_detail_base = InvitationDetailBase(
            id=invitation.id,
            email=invitation.email,
            applet_id=invitation.applet_id,
            applet_name=applet_name,
            role=invitation.role,
            key=invitation.key,
            status=invitation.status,
            invitor_id=invitation.invitor_id,
            first_name=first_name,
            last_name=last_name,
            created_at=invitation.created_at,
        )
        if invitation.role == Role.RESPONDENT:
            return InvitationDetailRespondent(
                meta=invitation.meta,
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

    async def get_by_email_applet_role_respondent(
        self, email_: str, applet_id_: uuid.UUID
    ) -> list[InvitationRespondent]:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.email == email_)
        query = query.where(InvitationSchema.applet_id == applet_id_)
        query = query.where(InvitationSchema.role == Role.RESPONDENT)
        db_result: Result = await self._execute(query)
        results: list[InvitationSchema] = db_result.scalars().all()

        return [
            InvitationRespondent.from_orm(invitation) for invitation in results
        ]

    async def get_by_email_applet_role_reviewer(
        self, email_: str, applet_id_: uuid.UUID
    ) -> list[InvitationReviewer]:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.email == email_)
        query = query.where(InvitationSchema.applet_id == applet_id_)
        query = query.where(InvitationSchema.role == Role.REVIEWER)
        db_result: Result = await self._execute(query)
        results: list[InvitationSchema] = db_result.scalars().all()

        return [
            InvitationReviewer.from_orm(invitation) for invitation in results
        ]

    async def get_by_email_applet_role_managers(
        self, email_: str, applet_id_: uuid.UUID, role_: ManagersRole
    ) -> list[InvitationManagers]:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.email == email_)
        query = query.where(InvitationSchema.applet_id == applet_id_)
        query = query.where(InvitationSchema.role == role_)
        db_result: Result = await self._execute(query)
        results: list[InvitationSchema] = db_result.scalars().all()

        return [
            InvitationManagers.from_orm(invitation) for invitation in results
        ]

    async def approve_by_id(self, id_: uuid.UUID):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.APPROVED)

        await self._execute(query)

    async def decline_by_id(self, id_: uuid.UUID):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.DECLINED)

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
    ) -> InvitationSchema | None:
        schema = self.schema_class
        query: Query = select(schema).where(
            schema.applet_id == applet_id,
            schema.role == Role.RESPONDENT,
            schema.status == status,
            schema.meta[text("'secret_user_id'")].astext == secret_user_id,
        )
        db_result = await self._execute(query)

        return db_result.scalars().first()
