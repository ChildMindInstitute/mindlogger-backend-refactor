from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    create_applet,
    delete_applet_by_id,
    get_applet_by_id,
    get_applets,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(get_applets)
router.get("/{id}")(get_applet_by_id)
router.post("/create")(create_applet)
router.delete("/delete/{id}")(delete_applet_by_id)
