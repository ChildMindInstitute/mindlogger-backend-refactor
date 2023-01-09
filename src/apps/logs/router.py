from fastapi.routing import APIRouter

from apps.logs.api.notification import (
    create_notification_log,
    get_notification_logs,
)

router = APIRouter(prefix="/logs", tags=["Logs"])

router.get("/notification", status_code=200)(get_notification_logs)
router.post("/notification", status_code=201)(create_notification_log)
