import uuid

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.domain import Alert, AlertTypes
from apps.shared.query_params import QueryParams


class AlertService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def get_all_alerts(self, filters: QueryParams) -> list[Alert]:
        alerts = []
        schemas = await AlertCRUD(self.session).get_all_for_user(self.user_id, filters.page, filters.limit)
        for alert, applet_history, access, applet, workspace, subject, integrations in schemas:
            if integrations and "LORIS" in integrations:
                _secret_id = "Loris Integration"
            else:
                _secret_id = subject.secret_user_id if subject else "Anonymous"
            alerts.append(
                Alert(
                    id=alert.id,
                    is_watched=alert.is_watched,
                    applet_id=alert.applet_id,
                    applet_name=applet_history.display_name,
                    version=alert.version,
                    secret_id=_secret_id,
                    activity_id=alert.activity_id,
                    activity_item_id=alert.activity_item_id,
                    message=alert.alert_message,
                    created_at=alert.created_at,
                    answer_id=alert.answer_id,
                    encryption=applet.encryption,
                    image=applet_history.image,
                    workspace=workspace.workspace_name,
                    respondent_id=alert.respondent_id,
                    subject_id=alert.subject_id,
                    type=alert.type if alert.type else AlertTypes.ANSWER_ALERT,
                )
            )
        return alerts

    async def get_all_alerts_count(self) -> dict:
        count = await AlertCRUD(self.session).get_all_for_user_count(self.user_id)
        return count

    async def watch(self, alert_id: uuid.UUID):
        await AlertCRUD(self.session).watch(self.user_id, alert_id)
