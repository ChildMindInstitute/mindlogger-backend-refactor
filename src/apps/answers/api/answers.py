from fastapi import Body, Depends

from apps.answers.crud import AnswerCRUD
from apps.answers.domain import AnswerCreate, AnswerCreateRequest
from apps.authentication.deps import get_current_user
from apps.shared.errors import NoContentError
from apps.users.domain import User


async def answer_create(
    user: User = Depends(get_current_user),
    schema: AnswerCreateRequest = Body(...),
) -> None:

    answer_create = AnswerCreate(
        user_id=user.id,
        applet_history_id_version=schema.activity_history_id_version,
        activity_history_id_version=schema.activity_item_history_id_version,
        activity_item_history_id_version=schema.activity_item_history_id_version,
        flow_history_id_version=schema.flow_history_id_version,
        flow_item_history_id_version=schema.flow_item_history_id_version,
        answer=schema.answer,
    )
    await AnswerCRUD().save(schema=answer_create)

    raise NoContentError
