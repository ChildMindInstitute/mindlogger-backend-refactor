from fastapi import APIRouter

from apps.alerts.ws_api import ws_get_alert_messages

router = APIRouter(prefix="/ws", tags=["Alerts websocket."])

router.websocket("/alerts")(ws_get_alert_messages)
