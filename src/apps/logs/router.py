from fastapi.routing import APIRouter

from apps.logs.api.notification import (
    notification_log_create,
    notification_log_retrieve,
)

router = APIRouter(prefix="/logs", tags=["Logs"])

router.get("/notification", status_code=200)(notification_log_retrieve)
router.post("/notification", status_code=201)(notification_log_create)
