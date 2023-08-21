from functools import partial
from urllib.parse import quote

from botocore.exceptions import ClientError
from fastapi import Body, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from apps.authentication.deps import get_current_user
from apps.file.domain import (
    FileCheckRequest,
    FileDownloadRequest,
    FileExistenceResponse,
    UploadedFile,
)
from apps.file.errors import FileNotFoundError
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from config import settings
from infrastructure.utility.cdn_client import CDNClient


async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    fileId: str | None = None,
) -> Response[UploadedFile]:
    cdn_client = CDNClient(settings.cdn, env=settings.env)
    key = fileId or CDNClient.generate_key(hash(user.id), file.filename)

    cdn_client.upload(key, file.file)

    result = UploadedFile(
        key=key, url=quote(settings.cdn.url.format(key=key), "/:")
    )
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


async def check_file_uploaded(
    schema: FileCheckRequest,
    user: User = Depends(get_current_user),
) -> None:
    """Provides the information if the file is uploaded."""

    cdn_client = CDNClient(settings.cdn, env=settings.env)
    results: list[FileExistenceResponse] = []

    for file_key in schema.files:
        cleaned_file_key = file_key.strip()
        file_existence_factory = partial(
            FileExistenceResponse,
            file_id=cleaned_file_key,
        )

        try:
            cdn_client.check_existence(cleaned_file_key)
            results.append(
                file_existence_factory(
                    uploaded=True,
                    remote_url=f"{cdn_client.client._endpoint.host}/{file_key}",
                )
            )
        except NotFoundError:
            results.append(file_existence_factory(uploaded=False))

    return ResponseMulti[FileExistenceResponse](
        result=results, count=len(results)
    )
