from fastapi.routing import APIRouter

from apps.notification.api.notification import create_log, get_logs

router = APIRouter(prefix="/notification", tags=["Notification"])

router.get("/logs")(get_logs)
router.post("/logs")(create_log)
