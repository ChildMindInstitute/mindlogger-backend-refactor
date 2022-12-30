from fastapi.routing import APIRouter

from apps.logs.api.notification import (
    create_notification_log,
    get_notification_logs,
)

router = APIRouter(prefix="/logs", tags=["Logs"])

router.get("/notification")(get_notification_logs)
router.post("/notification")(create_notification_log)
