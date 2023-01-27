from fastapi import Body, Depends

from apps.answers.crud import AnswerActivityItemsCRUD
from apps.answers.domain import (
    AnswerActivityItemsCreate,
    AnswerActivityItemsCreateRequest,
    PublicAnswerActivityItem,
)
from apps.answers.errors import UserDoesNotHavePermissionError
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccessItem
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.users.domain import User


async def answer_activity_item_create(
    id_version: str,
    user: User = Depends(get_current_user),
    schema: AnswerActivityItemsCreateRequest = Body(...),
) -> Response[PublicAnswerActivityItem]:

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

    # Create answer activity items and saving it to the database
    # TODO: Align with BA about the "answer" encryption
    answer = AnswerActivityItemsCreate(
        activity_item_history_id_version=id_version,
        respondent_id=user.id,
        **schema.dict(),
    )

    answer_activity_item = await AnswerActivityItemsCRUD().save(schema=answer)

    # Create public answer activity item model
    public_answer_activity_item = PublicAnswerActivityItem(
        **answer_activity_item.dict()
    )

    return Response(result=public_answer_activity_item)
