import asyncio
import datetime
import mimetypes
import os
import uuid
from functools import partial
from urllib.parse import quote

import aiofiles
import pytz
from botocore.exceptions import ClientError
from fastapi import Body, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqResult, TaskiqResultTimeoutError

from apps.authentication.deps import get_current_user
from apps.file.domain import (
    AnswerUploadedFile,
    ContentUploadedFile,
    FileCheckRequest,
    FileDownloadRequest,
    FileExistenceResponse,
    FilePresignRequest,
    LogFileExistenceResponse,
)
from apps.file.enums import FileScopeEnum
from apps.file.errors import FileNotFoundError
from apps.file.services import LogFileService
from apps.file.storage import select_storage
from apps.file.tasks import convert_audio_file, convert_image
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from apps.users.services.user import UserService
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
    converters = [convert_not_supported_audio]

    to_close = []
    to_delete = []
    try:
        res = None
        for converter in converters:
            if (res := await converter(file)) is not None:
                break

        if res is not None:
            filename, fout = res
            to_delete.append(fout)

            reader = open(fout, "rb")
            to_close.append(reader)
        else:
            filename = file.filename
            reader = file.file  # type: ignore[assignment]

        key = cdn_client.generate_key(
            FileScopeEnum.CONTENT, user.id, f"{uuid.uuid4()}/{filename}"
        )
        await cdn_client.upload(key, reader)
    finally:
        for f in to_close:
            f.close()

        for path in to_delete:
            os.remove(path)
    result = ContentUploadedFile(
        key=key, url=quote(settings.cdn.url.format(key=key), "/:")
    )
    return Response(result=result)


async def _copy(file: UploadFile, path: str):
    async with aiofiles.open(path, "wb") as fout:
        _size = 1024 * 1024
        while content := await file.read(_size):
            await fout.write(content)


async def convert_not_supported_audio(file: UploadFile):
    type_ = mimetypes.guess_type(file.filename)[0] or ""
    if type_.lower() == "video/webm":
        # store file, create task to convert
        convert_filename = f"{uuid.uuid4()}_{file.filename}"
        path = settings.uploads_dir / convert_filename
        await _copy(file, path)
        task = await convert_audio_file.kiq(convert_filename)
        task_result: TaskiqResult[str] = await task.wait_result(
            timeout=settings.task_audio_file_convert.task_wait_timeout
        )
        success = not task_result.is_err
        if not success:
            if task_result.error:
                raise task_result.error
            raise Exception("File convertion error")

        out_filename = task_result.return_value

        fout = settings.uploads_dir / out_filename

        return out_filename, fout

    return None


async def convert_not_supported_image(file: UploadFile):
    type_ = mimetypes.guess_type(file.filename)[0] or ""
    if type_.lower() == "image/heic":
        # store file, create task to convert
        convert_filename = f"{uuid.uuid4()}_{file.filename}"
        path = settings.uploads_dir / convert_filename
        await _copy(file, path)
        task = await convert_image.kiq(convert_filename)
        try:
            task_result: TaskiqResult[str] = await task.wait_result(
                timeout=settings.task_image_convert.task_wait_timeout
            )
        except TaskiqResultTimeoutError:
            raise

        success = not task_result.is_err

        if not success:
            if task_result.error:
                raise task_result.error
            raise Exception("File convertion error")

        out_filename = task_result.return_value

        fout = settings.uploads_dir / out_filename

        return out_filename, fout

    return None


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

    converters = [convert_not_supported_image]

    to_close = []
    to_delete = []
    try:
        res = None
        for converter in converters:
            if (res := await converter(file)) is not None:
                break

        if res is not None:
            filename, fout = res
            to_delete.append(fout)

            reader = open(fout, "rb")
            to_close.append(reader)
        else:
            filename = file.filename
            reader = file.file  # type: ignore[assignment]

        cdn_client = await select_storage(applet_id, session)
        unique = f"{user.id}/{applet_id}"
        cleaned_file_id = (
            file_id.strip() if file_id else f"{uuid.uuid4()}/{filename}"
        )
        key = cdn_client.generate_key(
            FileScopeEnum.ANSWER, unique, cleaned_file_id
        )
        await cdn_client.upload(key, reader)
    finally:
        for f in to_close:
            f.close()

        for path in to_delete:
            os.remove(path)

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
    return ResponseMulti[str | None](result=links, count=len(links))  # noqa


async def logs_upload(
    device_id: str,
    file_id: str = Query(..., alias="fileId"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
):
    service = LogFileService(user.id, cdn_client)
    try:
        key = service.key(device_id=device_id, file_name=file.filename)
        await service.upload(device_id, file, file_id)
        url = await cdn_client.generate_presigned_url(key)
        result = AnswerUploadedFile(key=key, url=url, file_id=file_id)
        await service.backend_log_upload(file_id, True, key)
        return Response(result=result)
    except Exception as ex:
        await service.backend_log_upload(file_id, False, str(ex))
        raise ex


async def logs_download(
    device_id: str,
    user_email: str,
    days: int,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
    session: AsyncSession = Depends(get_session),
):
    user_service = UserService(session)
    log_user = await user_service.get_by_email(user_email)
    service = LogFileService(log_user.id, cdn_client)
    try:
        UserAccessService.raise_for_developer_access(user.email_encrypted)
        end = datetime.datetime.now(tz=pytz.UTC)
        start = end - datetime.timedelta(days=days)
        files = await service.log_list(device_id, start, end)
        futures = []
        for key in map(lambda f: f["Key"], files):
            futures.append(cdn_client.generate_presigned_url(key))
        result = await asyncio.gather(*futures)
        await service.backend_log_download(
            user.email_encrypted, None, device_id, True
        )
        return ResponseMulti[str](result=result, count=len(result))
    except Exception as ex:
        await service.backend_log_download(
            user.email_encrypted, str(ex), device_id, False
        )
        raise ex


async def logs_exist_check(
    device_id: str,
    files: FileCheckRequest,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
):
    service = LogFileService(user.id, cdn_client)
    try:
        result = await service.check_exist(device_id, files.files)
        count = len(result)
        await service.backend_log_check(result, True, None)
        return ResponseMulti[LogFileExistenceResponse](
            result=result, count=count
        )
    except Exception as ex:
        await service.backend_log_check([], False, str(ex))
        raise ex
