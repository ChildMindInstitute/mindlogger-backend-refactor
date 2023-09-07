import uuid

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.domain import Alert
from apps.shared.encryption import decrypt
from apps.shared.query_params import QueryParams


class AlertService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def get_all_alerts(self, filters: QueryParams) -> list[Alert]:
        alerts = []
        schemas = await AlertCRUD(self.session).get_all_for_user(
            self.user_id, filters.page, filters.limit
        )

        for alert, applet_history, access, applet, workspace in schemas:
            try:
                plain_message = decrypt(
                    bytes.fromhex(alert.alert_message)
                ).decode("utf-8")
            except ValueError:
                plain_message = alert.alert_message
            alerts.append(
                Alert(
                    id=alert.id,
                    is_watched=alert.is_watched,
                    applet_id=alert.applet_id,
                    applet_name=applet_history.display_name,
                    version=alert.version,
                    secret_id=access.meta.get("secretUserId", "Anonymous"),
                    activity_id=alert.activity_id,
                    activity_item_id=alert.activity_item_id,
                    message=plain_message,
                    created_at=alert.created_at,
                    answer_id=alert.answer_id,
                    encryption=applet.encryption,
                    image=applet_history.image,
                    workspace=workspace.workspace_name,
                    respondent_id=alert.respondent_id,
                )
            )
        return alerts

    async def get_all_alerts_count(self) -> dict:
        count = await AlertCRUD(self.session).get_all_for_user_count(
            self.user_id
        )
        return count

    async def watch(self, alert_id: uuid.UUID):
        await AlertCRUD(self.session).watch(self.user_id, alert_id)
