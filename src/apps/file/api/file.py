from functools import partial
import uuid
from urllib.parse import quote

from botocore.exceptions import ClientError
from fastapi import Body, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_user
from apps.file.domain import (
    FileCheckRequest,
    FileDownloadRequest,
    FileExistenceResponse,
    UploadedFile,
)
from apps.file.errors import FileNotFoundError
from apps.file.storage import select_storage
from apps.shared.domain.response import Response
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from config import settings
from infrastructure.database.deps import get_session
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


async def answer_upload(
    applet_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cdn_client = await select_storage(applet_id, session)
    key = cdn_client.generate_key(hash(user.id), file.filename)
    cdn_client.upload(key, file.file)
    result = UploadedFile(
        key=key, url=quote(settings.cdn.url.format(key=key), "/:")
    )
    return Response(result=result)


async def answer_download(
    applet_id: uuid.UUID,
    request: FileDownloadRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cdn_client = await select_storage(applet_id, session)
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
) -> ResponseMulti[FileExistenceResponse]:
    """Provides the information if the files is uploaded."""

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
                    remote_url=f"{cdn_client.client._endpoint.host}"
                    f"/{file_key}",
                )
            )
        except NotFoundError:
            results.append(file_existence_factory(uploaded=False))

    return ResponseMulti[FileExistenceResponse](
        result=results, count=len(results)
    )
