import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Query

from apps.activities.db.schemas import ReusableItemChoiceSchema
from apps.alerts.db.schemas import AlertSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.folders.db.schemas import FolderSchema
from apps.integrations.loris.db.schemas import ConsentSchema, MlLorisUserRelationshipSchema
from apps.invitations.db import InvitationSchema
from apps.schedule.db.schemas import EventHistorySchema, EventSchema
from apps.subjects.db.schemas import SubjectSchema
from apps.themes.db.schemas import ThemeSchema
from apps.transfer_ownership.db import TransferSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema

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
