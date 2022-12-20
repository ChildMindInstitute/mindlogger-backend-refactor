import uuid

from botocore.exceptions import ClientError  # type: ignore
from fastapi import Body, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from apps.authentication.deps import get_current_user
from apps.file.domain import FileDownloadRequest, UploadedFile
from apps.file.errors import FileNotFoundError
from apps.shared.domain.response import Response
from apps.users.domain import User
from config import settings
from infrastructure.utility.cdn_client import CDNClient


async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> Response[UploadedFile]:
    cdn_client = CDNClient(settings.cdn, env=settings.env)

    # generate key
    key = CDNClient.generate_key(str(uuid.uuid4()), file.filename)

    # upload file
    cdn_client.upload(key, file.file)

    result = UploadedFile(key=key)
    return Response(result=result)


async def download(
    request: FileDownloadRequest = Body(...),
    user: User = Depends(get_current_user),
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
