from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    applet_create,
    applet_delete,
    applet_list,
    applet_retrieve,
    applet_update,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(applet_list)
router.post("", status_code=201)(applet_create)
router.put("/{id_}", status_code=200)(applet_update)
router.get("/{id_}")(applet_retrieve)
router.delete("/{id_}", status_code=204)(applet_delete)
