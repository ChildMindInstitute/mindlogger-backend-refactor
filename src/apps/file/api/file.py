import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.parse import quote

from botocore.exceptions import ClientError
from fastapi import Body, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_user
from apps.file.constants import FileScope
from apps.file.domain import (
    FileCheckRequest,
    FileDownloadRequest,
    FileExistenceResponse,
    FilePresignedResponse,
    FilePresignRequest,
    UploadedFile,
)
from apps.file.errors import FileNotFoundError
from apps.file.services import PresignedUrlsGeneratorService
from apps.file.storage import select_storage
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.errors import AnswerViewAccessDenied
from config import settings
from infrastructure.database.deps import get_session
from infrastructure.utility.cdn_client import CDNClient


async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> Response[UploadedFile]:
    cdn_client = CDNClient(settings.cdn, env=settings.env)
    key = CDNClient.generate_key(
        FileScope.CONTENT,
        user.id,
        file.filename,
    )
    with ThreadPoolExecutor() as executor:
        future = executor.submit(cdn_client.upload, key, file.file)
    await asyncio.wrap_future(future)
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
    file_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not await AppletAccessCRUD(session).can_see_data(
        applet_id=applet_id, user_id=user.id
    ):
        raise AnswerViewAccessDenied()

    cdn_client = await select_storage(applet_id, session)
    unique = f"{applet_id}/{user.id}"
    cleaned_file_id = file_id.strip()
    key = CDNClient.generate_key(FileScope.ANSWER, unique, cleaned_file_id)
    with ThreadPoolExecutor() as executor:
        future = executor.submit(cdn_client.upload, key, file.file)
    await asyncio.wrap_future(future)
    result = UploadedFile(key=key, url=key)
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
    applet_id: uuid.UUID,
    schema: FileCheckRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResponseMulti[FileExistenceResponse]:
    """Provides the information if the files is uploaded."""

    if not await AppletAccessCRUD(session).can_see_data(
        applet_id=applet_id, user_id=user.id
    ):
        raise AnswerViewAccessDenied()

    cdn_client = CDNClient(settings.cdn, env=settings.env)
    results: list[FileExistenceResponse] = []

    for file_id in schema.files:
        cleaned_file_id = file_id.strip()

        unique = f"{applet_id}/{user.id}"
        key = CDNClient.generate_key(FileScope.ANSWER, unique, cleaned_file_id)

        file_existence_factory = partial(
            FileExistenceResponse,
            key=key,
        )

        try:
            cdn_client.check_existence(key)
            results.append(
                file_existence_factory(
                    uploaded=True,
                    url=quote(settings.cdn.url.format(key=key), "/:"),
                )
            )
        except NotFoundError:
            results.append(file_existence_factory(uploaded=False))

    return ResponseMulti[FileExistenceResponse](
        result=results, count=len(results)
    )


async def presign(
    applet_id: uuid.UUID,
    request: FilePresignRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not await AppletAccessCRUD(session).can_see_data(
        applet_id=applet_id, user_id=user.id
    ):
        raise AnswerViewAccessDenied()

    results: list[
        FilePresignedResponse
    ] = await PresignedUrlsGeneratorService()(
        session=session,
        applet_id=applet_id,
        given_private_urls=request.private_urls,
    )

    return ResponseMulti[FilePresignedResponse](
        result=results, count=len(results)
    )
