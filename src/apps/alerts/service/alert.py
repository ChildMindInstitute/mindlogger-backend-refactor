import uuid

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert import AlertCreate
from apps.alerts.domain.alert_config import AlertConfigGet
from apps.alerts.errors import AlertConfigNotFoundError
from apps.answers.domain import AppletAnswerCreate


class AlertService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def create_alert(self, schema: AppletAnswerCreate):
        for item_id in schema.answer.item_ids:  # type: ignore
            try:
                alert_config = await AlertConfigsCRUD(
                    self.session
                ).get_by_applet_item_answer(
                    AlertConfigGet(
                        applet_id=schema.applet_id,
                        activity_item_histories_id_version=(
                            f"{item_id}_{schema.version}"
                        ),
                        specific_answer=schema.answer.answer,  # type: ignore
                    )
                )
            except AlertConfigNotFoundError:
                continue
            if alert_config:
                await AlertCRUD(self.session).save(
                    AlertCreate(
                        specific_answer=schema.answer.answer,  # type: ignore
                        respondent_id=self.user_id,
                        alert_config_id=alert_config.id,
                        applet_id=schema.applet_id,
                        alert_message=alert_config.alert_message,
                        activity_item_histories_id_version=(
                            f"{item_id}_{schema.version}"
                        ),
                    )
                )
