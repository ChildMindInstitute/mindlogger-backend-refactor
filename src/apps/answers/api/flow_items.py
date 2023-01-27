from fastapi import Body, Depends

from apps.answers.crud import AnswerFlowItemsCRUD
from apps.answers.domain import (
    AnswerFlowItemsCreate,
    AnswerFlowItemsCreateRequest,
    PublicAnswerFlowItem,
)
from apps.answers.errors import UserDoesNotHavePermissionError
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccessItem
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.users.domain import User


async def answer_flow_item_create(
    id_version: str,
    user: User = Depends(get_current_user),
    schema: AnswerFlowItemsCreateRequest = Body(...),
) -> Response[PublicAnswerFlowItem]:

    user_applet_access_item = UserAppletAccessItem(
        user_id=user.id,
        applet_id=schema.applet_id,
        role=Role("respondent"),
    )

    # Checking if the user has responder permission to the given applet
    user_applet_access = await UserAppletAccessCRUD().get_by_user_applet_role(
        **user_applet_access_item.dict()
    )

    if not user_applet_access:
        raise UserDoesNotHavePermissionError

    # Create answer flow items and saving it to the database
    # TODO: Align with BA about the "answer" encryption
    answer = AnswerFlowItemsCreate(
        flow_item_history_id_version=id_version,
        respondent_id=user.id,
        **schema.dict(),
    )

    answer_flow_item = await AnswerFlowItemsCRUD().save(schema=answer)

    # Create public answer flow item model
    public_answer_flow_item = PublicAnswerFlowItem(**answer_flow_item.dict())

    return Response(result=public_answer_flow_item)
