from fastapi.routing import APIRouter

from apps.file.api.file import check_file_uploaded, download, upload

router = APIRouter(prefix="/file", tags=["File"])

router.post(
    "/upload",
    description="""Used for uploading images and files related to applets.
                Receives file object, returns key as a path to S3 Bucket.""",
)(upload)

router.post(
    "/download",
    description="""Used for downloading images and files related to applets.
                Receives key as a path to S3 Bucket, returns file object.""",
)(download)

router.post("/upload/check")(check_file_uploaded)
