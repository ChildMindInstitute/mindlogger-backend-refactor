from fastapi import Body, Depends

from apps.answers.domain import AppletAnswerCreate
from apps.answers.service import AnswerService
from apps.authentication.deps import get_current_user
from apps.users.domain import User
from infrastructure.database import atomic, session_manager


async def create_answer(
    user: User = Depends(get_current_user),
    schema: AppletAnswerCreate = Body(...),
    session=Depends(session_manager.get_session),
) -> None:
    async with atomic(session):
        await AnswerService(session, user.id).create_answer(schema)
    return
