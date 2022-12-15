import uuid

from botocore.exceptions import ClientError  # type: ignore
from fastapi import Body, File, UploadFile
from fastapi.responses import StreamingResponse

from apps.file.domain import FileDownloadRequest, UploadedFile
from apps.file.errors import FileNotFoundError
from apps.shared.domain.response import Response
from config import settings
from infrastructure.utility.cdn_client import CDNClient


# TODO: Require Authentication
async def upload(
    file: UploadFile = File(...),
) -> Response[UploadedFile]:
    cdn_client = CDNClient(settings.cdn, env=settings.env)

    # generate key
    key = CDNClient.generate_key(str(uuid.uuid4()), file.filename)
    print(file.content_type)

    # upload file
    try:
        cdn_client.upload(key, file.file)
    except Exception as e:
        raise e
    result = UploadedFile(key=key)
    return Response(result=result)


# TODO: Require Authentication
async def download(
    request: FileDownloadRequest = Body(...),
) -> StreamingResponse:

    # download file by given key
    cdn_client = CDNClient(settings.cdn, env=settings.env)

    try:
        file, media_type = cdn_client.download(request.key)

    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise FileNotFoundError
        else:
            raise e

    return StreamingResponse(file, media_type=media_type)
