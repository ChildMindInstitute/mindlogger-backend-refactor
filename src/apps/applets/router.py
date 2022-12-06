from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    create_applet,
    get_applet_by_id,
    get_applets_user_admin,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.post("/applet/create")(create_applet)
router.get("/applet/{id}")(get_applet_by_id)
router.get("/admin-applets")(get_applets_user_admin)
