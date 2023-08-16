from fastapi.routing import APIRouter

from apps.file.api.file import answer_download, answer_upload, download, upload

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


router.post(
    "/{applet_id}/upload",
    description=(
        "Used for uploading images and files related to applets."
        "File stored in S3 account or arbitrary storage(S3, AzureBlob)"
    ),
)(answer_upload)


router.post(
    "/{applet_id}/download",
    description=(
        "Used for downloading images and files related to applets."
        "File stored in S3 account or arbitrary storage(S3, AzureBlob)"
    ),
)(answer_download)
