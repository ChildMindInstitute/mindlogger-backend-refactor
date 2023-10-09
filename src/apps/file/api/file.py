import asyncio
import datetime
import uuid
from functools import partial
from urllib.parse import quote

import pytz
from botocore.exceptions import ClientError
from fastapi import Body, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.deps import get_current_user
from apps.file.domain import (
    AnswerUploadedFile,
    ContentUploadedFile,
    FileCheckRequest,
    FileDownloadRequest,
    FileExistenceResponse,
    FilePresignRequest,
)
from apps.file.enums import FileScopeEnum
from apps.file.errors import FileNotFoundError
from apps.file.services import LogFileService
from apps.file.storage import select_storage
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import FieldError, NotFoundError
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import AnswerViewAccessDenied
from apps.workspaces.service.user_access import UserAccessService
from config import settings
from infrastructure.database.deps import get_session
from infrastructure.dependency.cdn import get_log_bucket, get_media_bucket
from infrastructure.dependency.presign_service import get_presign_service
from infrastructure.utility.cdn_client import CDNClient


async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_media_bucket),
) -> Response[ContentUploadedFile]:
    key = cdn_client.generate_key(
        FileScopeEnum.CONTENT, user.id, f"{uuid.uuid4()}/{file.filename}"
    )
    await cdn_client.upload(key, file.file)
    result = ContentUploadedFile(
        key=key, url=quote(settings.cdn.url.format(key=key), "/:")
    )
    return Response(result=result)


async def download(
    request: FileDownloadRequest = Body(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_media_bucket),
) -> StreamingResponse:
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
    file_id=Query(None, alias="fileId"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not await UserAppletAccessCRUD(session).get_by_roles(
        user.id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    ):
        raise AnswerViewAccessDenied()

    cdn_client = await select_storage(applet_id, session)
    unique = f"{user.id}/{applet_id}"
    cleaned_file_id = (
        file_id.strip() if file_id else f"{uuid.uuid4()}/{file.filename}"
    )
    key = cdn_client.generate_key(
        FileScopeEnum.ANSWER, unique, cleaned_file_id
    )
    await cdn_client.upload(key, file.file)
    result = AnswerUploadedFile(
        key=key,
        url=cdn_client.generate_private_url(key),
        file_id=cleaned_file_id,
    )
    return Response(result=result)


async def answer_download(
    applet_id: uuid.UUID,
    request: FileDownloadRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cdn_client = await select_storage(applet_id, session)
    if request.key.startswith(LogFileService.LOG_KEY):
        LogFileService.raise_for_access(user.email)

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

    if not await UserAppletAccessCRUD(session).get_by_roles(
        user.id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    ):
        raise AnswerViewAccessDenied()

    cdn_client = await select_storage(applet_id, session)
    results: list[FileExistenceResponse] = []

    for file_id in schema.files:
        cleaned_file_id = file_id.strip()

        unique = f"{user.id}/{applet_id}"
        key = cdn_client.generate_key(
            FileScopeEnum.ANSWER, unique, cleaned_file_id
        )

        file_existence_factory = partial(
            FileExistenceResponse,
            key=key,
            file_id=file_id,
        )

        try:
            await cdn_client.check_existence(key)
            results.append(
                file_existence_factory(
                    uploaded=True,
                    url=cdn_client.generate_private_url(key),
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
    service = await get_presign_service(applet_id, user.id, session)
    links = await service.presign(request.private_urls)
    return ResponseMulti[str](result=links, count=len(links))


async def logs_upload(
    device_id: str,
    file_id=Query(None, alias="fileId"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
):
    if not file_id:
        err = FieldError()
        err.zero_path = "query"
        raise err

    service = LogFileService(user.id, cdn_client)
    key = service.key(device_id=device_id, file_name=file.filename)
    await service.upload(device_id, file, file_id)
    result = AnswerUploadedFile(
        key=key,
        url=quote(settings.cdn.url.format(key=key), "/:"),
        file_id=file_id,
    )
    return Response(result=result)


async def logs_download(
    device_id: str,
    user_id: uuid.UUID,
    days: int,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
):
    UserAccessService.raise_for_developer_access(user.email_encrypted)
    service = LogFileService(user_id, cdn_client)
    end = datetime.datetime.now(tz=pytz.UTC)
    start = end - datetime.timedelta(days=days)
    files = await service.log_list(device_id, start, end)
    futures = []
    for key in map(lambda f: f["Key"], files):
        futures.append(cdn_client.generate_presigned_url(key))
    result = await asyncio.gather(*futures)
    return ResponseMulti[str](result=result, count=len(result))


async def logs_exist_check(
    device_id: str,
    files: FileCheckRequest,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
):
    service = LogFileService(user.id, cdn_client)
    result = await service.check_exist(device_id, files.files)
    count = len(result)
    return ResponseMulti[FileExistenceResponse](result=result, count=count)
