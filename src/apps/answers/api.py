from fastapi import Body, Depends

from apps.answers.domain import AppletAnswerCreate
from apps.answers.service import AnswerService
from apps.authentication.deps import get_current_user
from apps.users.domain import User


async def create_answer(
    user: User = Depends(get_current_user),
    schema: AppletAnswerCreate = Body(...),
) -> None:
    await AnswerService(user.id).create_answer(schema)
    return
