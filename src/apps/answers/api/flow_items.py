from fastapi import Body, Depends

from apps.answers.crud import AnswerFlowItemsCRUD
from apps.answers.domain import (
    AnswerFlowCreate,
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
        role=Role.RESPONDENT,
    )

    # Checking if the user has responder permission to the given applet
    user_applet_access = await UserAppletAccessCRUD().get_by_user_applet_role(
        user_applet_access_item
    )

    if not user_applet_access:
        raise UserDoesNotHavePermissionError

    # Create answer flow items and saving it to the database
    # TODO: Align with BA about the "answer" encryption
    answers_with_id_version = AnswerFlowItemsCreate(
        applet_id=schema.applet_id,
        flow_item_history_id_version=(
            f"{schema.flow_item_history_id}_{schema.applet_history_version}"
        ),
        respondent_id=user.id,
        applet_history_id_version=(
            f"{schema.applet_id}_{schema.applet_history_version}"
        ),
        answers=[
            AnswerFlowCreate(
                **answer.dict(),
                activity_item_history_id_version=(
                    f"{answer.activity_item_history_id}_"
                    f"{schema.applet_history_version}"
                ),
            )
            for answer in schema.answers
        ],
    )

    answer_flow_items: list[AnswerFlowItem] = await AnswerFlowItemsCRUD().save(
        schema_multiple=answers_with_id_version
    )

    return ResponseMulti(
        result=[
            PublicAnswerFlowItem(**answer_flow_item.dict())
            for answer_flow_item in answer_flow_items
        ]
    )
