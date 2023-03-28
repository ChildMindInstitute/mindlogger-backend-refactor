import json
import uuid

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert import AlertCreate
from apps.alerts.domain.alert_config import AlertConfigGet
from apps.alerts.errors import AlertConfigNotFoundError
from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.answers.db.schemas import (
    AnswerActivityItemsSchema,
    AnswerFlowItemsSchema,
)
from apps.answers.domain import AppletAnswerCreate


class AlertService:
    def __init__(self, session, user_id: uuid.UUID | None):
        self.user_id = user_id
        self.session = session

    async def create_alert(self, applet_answer: AppletAnswerCreate):

        schemas = list()

        for answer in applet_answer.answers:
            activity_item_id_version = (
                f"{answer.activity_item_id}_{applet_answer.version}"
            )
            if applet_answer.flow_id:
                flow_id_version = (
                    f"{applet_answer.flow_id}_{applet_answer.version}"
                )
                # TODO: Do as for AnswerActivityItems
            else:
                schemas: list[AnswerActivityItemsSchema] = await AnswerActivityItemsCRUD(self.session).get(
                    applet_answer, self.user_id, activity_item_id_version
                )

        for schema in schemas:
            try:
                alert_config = (
                    await AlertConfigsCRUD(self.session).get_by_applet_item_answer(
                        AlertConfigGet(
                            applet_id=schema.applet_id,
                            activity_item_histories_id_version=(
                                schema.activity_item_history_id
                            ),
                            specific_answer=json.loads(schema.answer)["value"],
                        )
                    )
                )
            except AlertConfigNotFoundError:
                continue

            if alert_config:
                await AlertCRUD(self.session).save(
                    AlertCreate(
                        specific_answer=schema.answer,
                        respondent_id=schema.respondent_id,
                        alert_config_id=alert_config.id,
                        applet_id=schema.applet_id,
                        alert_message=alert_config.alert_message,
                        activity_item_histories_id_version=(
                            schema.activity_item_history_id
                        ),
                    )
                )
