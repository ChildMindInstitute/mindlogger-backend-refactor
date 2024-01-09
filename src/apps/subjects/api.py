from fastapi import Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.subjects.domain import Subject, SubjectCreateRequest
from apps.subjects.services import SubjectsService
from apps.users import User
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def create_subject(
    user: User = Depends(get_current_user),
    schema: SubjectCreateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> Response[Subject]:
    async with atomic(session):
        subject_sch = Subject(
            applet_id=schema.applet_id,
            creator_id=user.id,
            language=schema.language,
        )
        subject = await SubjectsService(session, user.id).create(subject_sch)
        return Response(result=Subject.from_orm(subject))
