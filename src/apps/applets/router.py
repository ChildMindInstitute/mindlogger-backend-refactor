from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    create_applet,
    delete_applet_by_id,
    get_applet_by_id,
    get_applets,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(get_applets)
router.post("")(create_applet)
router.get("/{id_}")(get_applet_by_id)
router.delete("/{id_}")(delete_applet_by_id)
