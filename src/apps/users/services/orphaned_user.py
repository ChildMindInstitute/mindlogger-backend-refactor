import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Query

from apps.activities.db.schemas import ReusableItemChoiceSchema
from apps.alerts.db.schemas import AlertSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.folders.db.schemas import FolderSchema
from apps.integrations.loris.db.schemas import ConsentSchema, MlLorisUserRelationshipSchema
from apps.invitations.db import InvitationSchema
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.library.db.schemas import CartSchema
from apps.logs.db.schemas import NotificationLogSchema
from apps.schedule.db.schemas import EventHistorySchema, EventSchema, UserDeviceEventsHistorySchema
from apps.subjects.db.schemas import SubjectSchema
from apps.themes.db.schemas import ThemeSchema
from apps.transfer_ownership.db import TransferSchema
from apps.users.db.schemas import UserDeviceSchema, UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema, UserWorkspaceSchema

# Any row in these columns, even soft deleted, means the user is not orphaned
BLOCKING_COLUMNS: list[InstrumentedAttribute] = [
    SubjectSchema.user_id,
    SubjectSchema.creator_id,
    UserAppletAccessSchema.user_id,
    UserAppletAccessSchema.owner_id,
    UserAppletAccessSchema.invitor_id,
    AppletSchema.creator_id,
    AppletHistorySchema.user_id,
    InvitationSchema.user_id,
    InvitationSchema.invitor_id,
    TransferSchema.from_user_id,
    TransferSchema.to_user_id,
    AlertSchema.user_id,
    AlertSchema.respondent_id,
    EventSchema.user_id,
    EventHistorySchema.user_id,
    EventHistorySchema.updated_by,
    FolderSchema.workspace_id,
    FolderSchema.creator_id,
    ThemeSchema.creator_id,
    ReusableItemChoiceSchema.user_id,
    ConsentSchema.user_id,
    MlLorisUserRelationshipSchema.ml_user_uuid,
    AnswerSchema.respondent_id,
    AnswerItemSchema.respondent_id,
    AnswerNoteSchema.user_id,
]

# The user's own rows, deleted together with the user
OWN_COLUMNS: list[InstrumentedAttribute] = [
    UserDeviceEventsHistorySchema.user_id,
    UserDeviceSchema.user_id,
    CartSchema.user_id,
    LegalAcceptanceSchema.user_id,
    UserWorkspaceSchema.user_id,
]


class OrphanedUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_blocking_references(self, user_id: uuid.UUID) -> list[str]:
        references = []
        for column in BLOCKING_COLUMNS:
            query: Query = select(column).where(column == user_id).exists()
            if await self.session.scalar(select(query)):
                references.append(f"{column.class_.__tablename__}.{column.key}")
        return references

    async def delete_user(self, user_id: uuid.UUID) -> None:
        for column in OWN_COLUMNS:
            await self.session.execute(delete(column.class_).where(column == user_id))
        # notification_logs stores the user id as text
        await self.session.execute(delete(NotificationLogSchema).where(NotificationLogSchema.user_id == str(user_id)))
        await self.session.execute(delete(UserSchema).where(UserSchema.id == user_id))
