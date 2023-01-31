from fastapi import Body, Depends

from apps.answers.crud import AnswerFlowItemsCRUD
from apps.answers.domain import (
    AnswerFlowItem,
    AnswerFlowItemsCreate,
    AnswerFlowItemsCreateRequest,
    PublicAnswerFlowItem,
)
from apps.answers.errors import UserDoesNotHavePermissionError
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccessItem
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.users.domain import User


async def answer_flow_item_create(
    user: User = Depends(get_current_user),
    schema: AnswerFlowItemsCreateRequest = Body(...),
) -> ResponseMulti[PublicAnswerFlowItem]:

    user_applet_access_item = UserAppletAccessItem(
        user_id=user.id,
        applet_id=schema.applet_id,
        role=Role("respondent"),
    )

    # Checking if the user has responder permission to the given applet
    user_applet_access = await UserAppletAccessCRUD().get_by_user_applet_role(
        user_applet_access_item
    )

    if not user_applet_access:
        raise UserDoesNotHavePermissionError

    # Create answer flow items and saving it to the database
    # TODO: Align with BA about the "answer" encryption
    answers = AnswerFlowItemsCreate(
        respondent_id=user.id,
        **schema.dict(),
    )

    answer_flow_items: list[AnswerFlowItem] = await AnswerFlowItemsCRUD().save(
        schema_multiple=answers
    )

    return ResponseMulti(
        results=[
            PublicAnswerFlowItem(**answer_flow_item.dict())
            for answer_flow_item in answer_flow_items
        ]
    )
