from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    create_applet,
    delete_applet_by_id,
    get_applet_by_id,
    get_applets,
    update_applet,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(get_applets)
router.post("", status_code=201)(create_applet)
router.put("/{id_}", status_code=200)(update_applet)
router.get("/{id_}")(get_applet_by_id)
router.delete("/{id_}", status_code=204)(delete_applet_by_id)
