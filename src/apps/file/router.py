from fastapi.routing import APIRouter
from starlette import status

from apps.file.api.file import (
    answer_download,
    answer_upload,
    check_file_uploaded,
    download,
    presign,
    upload,
)
from apps.file.domain import FileExistenceResponse, UploadedFile
from apps.shared.domain import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    ResponseMulti,
)

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
    responses={
        status.HTTP_200_OK: {"model": UploadedFile},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(answer_upload)


router.post(
    "/{applet_id}/download",
    description=(
        "Used for downloading images and files related to applets."
        "File stored in S3 account or arbitrary storage(S3, AzureBlob)"
    ),
)(answer_download)

# router.post("/upload/check")(check_file_uploaded)
router.post(
    "/{applet_id}/upload/check",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[FileExistenceResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(check_file_uploaded)


router.post(
    "/{applet_id}/presign",
    description=(
        "Used for generating temporary public urls for files"
        "File stored in S3 account or arbitrary storage(S3, AzureBlob)"
    ),
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[str]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(presign)
