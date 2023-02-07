from fastapi.routing import APIRouter

from apps.applets.api.applets import (
    applet_create,
    applet_delete,
    applet_list,
    applet_retrieve,
    applet_set_folder,
    applet_unique_name_get,
    applet_update,
    applet_version_changes_retrieve,
    applet_version_retrieve,
    applet_versions_retrieve,
    folders_applet_get,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get("")(applet_list)
router.get("/folders/{id_}", status_code=200)(folders_applet_get)
router.get("/{id_}")(applet_retrieve)
router.get("/{id_}/versions")(applet_versions_retrieve)
router.get("/{id_}/versions/{version}")(applet_version_retrieve)
router.get("/{id_}/versions/{version}/changes")(
    applet_version_changes_retrieve
)

router.post("", status_code=201)(applet_create)
router.post("/set_folder", status_code=200)(applet_set_folder)
router.post("/unique_name", status_code=200)(applet_unique_name_get)

router.put("/{id_}", status_code=200)(applet_update)

router.delete("/{id_}", status_code=204)(applet_delete)
