from fastapi.routing import APIRouter

from apps.folders.api import (
    folder_create,
    folder_delete,
    folder_list,
    folder_update_name,
)

router = APIRouter(prefix="/folders", tags=["Folders"])

router.get("")(folder_list)
router.post("", status_code=201)(folder_create)
router.put("/{id_}", status_code=200)(folder_update_name)
router.delete("/{id_}", status_code=204)(folder_delete)
