from fastapi.routing import APIRouter

from apps.file.api.file import download, upload

router = APIRouter(prefix="/file", tags=["File"])

router.post("/upload")(upload)
router.get("/download")(download)
