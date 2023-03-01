import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import Role
from apps.invitations.constants import InvitationStatus
from apps.invitations.db import InvitationSchema
from apps.invitations.domain import (
    InvitationDetail,
    InvitationDetailBase,
    InvitationDetailRespondent,
    InvitationDetailReviewer,
)
from infrastructure.database import BaseCRUD


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

    async def get_pending_by_invitor_id(
        self, user_id: int
    ) -> list[InvitationDetail]:
        query: Query = select(
            InvitationSchema, AppletSchema.display_name.label("applet_name")
        )
        query = query.join(
            AppletSchema, AppletSchema.id == InvitationSchema.applet_id
        )
        query = query.where(InvitationSchema.invitor_id == user_id)
        query = query.where(
            InvitationSchema.status == InvitationStatus.PENDING
        )
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
                )
            )
        return results

    async def get_by_email_and_key(self, email: str, key: uuid.UUID):
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
        invitation_detail_base = InvitationDetailBase(
            id=invitation.id,
            email=invitation.email,
            applet_id=invitation.applet_id,
            applet_name=applet_name,
            role=invitation.role,
            key=invitation.key,
            status=invitation.status,
            invitor_id=invitation.invitor_id,
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

    async def get_by_email_applet_role(
        self, email_: str, applet_id_: int, role_: Role
    ) -> InvitationSchema:
        query: Query = select(InvitationSchema)
        query = query.where(InvitationSchema.email == email_)
        query = query.where(InvitationSchema.applet_id == applet_id_)
        query = query.where(InvitationSchema.role == role_)
        db_result: Result = await self._execute(query)
        result = db_result.scalars().all()

        return result

    async def approve_by_id(self, id_: int):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.APPROVED)

        await self._execute(query)

    async def decline_by_id(self, id_: int):
        query = update(InvitationSchema)
        query = query.where(InvitationSchema.id == id_)
        query = query.values(status=InvitationStatus.DECLINED)

        await self._execute(query)
