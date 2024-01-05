from fastapi import Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.shared.exception import NotFoundError
from apps.subjects.domain import Subject, SubjectCreateRequest
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.users.services.user import UserService
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def create_subject(
    user: User = Depends(get_current_user),
    schema: SubjectCreateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> Response[Subject]:
    async with atomic(session):
        access_srv = UserAppletAccessService(
            session, user.id, schema.applet_id
        )
        owner_access = await access_srv.get_owner()
        owner = await UserService(session).get(owner_access.user_id)
        if not owner:
            raise NotFoundError()
        subject_sch = Subject(
            applet_id=schema.applet_id,
            creator_id=user.id,
            user_id=owner_access.user_id,
            email=owner.email_encrypted,
        )
        subject = await SubjectsService(session, user.id).create(subject_sch)
        return Response(result=Subject.from_orm(subject))
