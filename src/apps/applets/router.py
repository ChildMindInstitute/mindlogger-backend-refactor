from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    applet_create,
    applet_delete,
    applet_list,
    applet_retrieve,
    applet_update,
    applet_version_changes_retrieve,
    applet_version_retrieve,
    applet_versions_retrieve,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(applet_list)
router.post("", status_code=201)(applet_create)
router.put("/{id_}", status_code=200)(applet_update)
router.get("/{id_}")(applet_retrieve)
router.get("/{id_}/versions")(applet_versions_retrieve)
router.get("/{id_}/versions/{version}")(applet_version_retrieve)
router.get("/{id_}/versions/{version}/changes")(
    applet_version_changes_retrieve
)
router.delete("/{id_}", status_code=204)(applet_delete)
