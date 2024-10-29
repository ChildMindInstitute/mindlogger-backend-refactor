import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject


async def get_applet_user_subject(session: AsyncSession, applet_id: uuid.UUID, user_id: uuid.UUID) -> Subject:
    query = select(SubjectSchema).where(SubjectSchema.applet_id == applet_id, SubjectSchema.user_id == user_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)
