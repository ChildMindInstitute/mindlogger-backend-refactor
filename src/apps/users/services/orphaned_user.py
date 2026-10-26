import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Query

from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.subjects.db.schemas import SubjectSchema
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
