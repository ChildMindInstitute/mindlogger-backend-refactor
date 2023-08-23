from fastapi.routing import APIRouter
from starlette import status

from apps.file.api.file import check_file_uploaded, download, upload
from apps.file.domain import FileExistenceResponse
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

# router.post("/upload/check")(check_file_uploaded)
router.get(
    "/upload/check",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[FileExistenceResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(check_file_uploaded)
