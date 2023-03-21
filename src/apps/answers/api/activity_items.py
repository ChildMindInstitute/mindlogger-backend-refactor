from fastapi import Body, Depends

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert import AlertCreate
from apps.alerts.domain.alert_config import AlertConfigGet
from apps.alerts.errors import AlertConfigNotFoundError
from apps.answers.crud import AnswerActivityItemsCRUD
from apps.answers.domain import (
    AnswerActivityItem,
    AnswerActivityItemsCreate,
    AnswerActivityItemsCreateRequest,
    AnswerCreate,
    PublicAnswerActivityItem,
)
from apps.answers.errors import UserDoesNotHavePermissionError
from apps.applets.crud import UserAppletAccessCRUD
from apps.applets.domain import Role, UserAppletAccessItem
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.users.domain import User


async def answer_activity_item_create(
    user: User = Depends(get_current_user),
    schema: AnswerActivityItemsCreateRequest = Body(...),
) -> ResponseMulti[PublicAnswerActivityItem]:

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

    # Create answer activity items and saving it to the database
    # TODO: Align with BA about the "answer" encryption
    answers_with_id_version = AnswerActivityItemsCreate(
        applet_id=schema.applet_id,
        activity_id=schema.activity_id,
        respondent_id=user.id,
        applet_history_id_version=(
            f"{schema.applet_id}_{schema.applet_history_version}"
        ),
        answers=[
            AnswerCreate(
                **answer.dict(),
                activity_item_history_id_version=(
                    f"{answer.activity_item_history_id}_"
                    f"{schema.applet_history_version}"
                ),
            )
            for answer in schema.answers
        ],
    )

    answer_activity_items: list[
        AnswerActivityItem
    ] = await AnswerActivityItemsCRUD().save(
        schema_multiple=answers_with_id_version
    )

    # Alerts create if alerts config for specific parameters exist
    for answer in schema.answers:
        try:
            alert_config = await AlertConfigsCRUD().get_by_applet_item_answer(
                AlertConfigGet(
                    applet_id=schema.applet_id,
                    activity_item_histories_id_version=(
                        f"{answer.activity_item_history_id}_"
                        f"{schema.applet_history_version}"
                    ),
                    specific_answer=answer.answer,
                )
            )
            await AlertCRUD().save(
                AlertCreate(
                    respondent_id=user.id,
                    alert_config_id=alert_config.id,
                    applet_id=schema.applet_id,
                    activity_item_histories_id_version=(
                        f"{answer.activity_item_history_id}_"
                        f"{schema.applet_history_version}"
                    ),
                    specific_answer=answer.answer,
                )
            )
        except AlertConfigNotFoundError:
            raise

    return ResponseMulti(
        result=[
            PublicAnswerActivityItem(**answer_activity_item.dict())
            for answer_activity_item in answer_activity_items
        ]
    )
