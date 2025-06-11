import asyncio
import datetime
import mimetypes
import os
import uuid
from functools import partial
from typing import cast
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
    FileIdRequest,
    FileNameRequest,
    FilePresignRequest,
    LogFileExistenceResponse,
    PresignedUrl,
    WebmTargetExtenstion,
)
from apps.file.enums import FileScopeEnum
from apps.file.errors import FileNotFoundError, SomethingWentWrongError
from apps.file.services import LogFileService
from apps.file.tasks import convert_audio_file, convert_image
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from apps.users.services.user import UserService
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import WorkspaceArbitrary
from apps.workspaces.errors import AnswerViewAccessDenied
from apps.workspaces.service.user_access import UserAccessService
from config import settings
from infrastructure.database.deps import get_session
from infrastructure.storage.buckets import get_log_bucket, get_media_bucket, get_operations_bucket
from infrastructure.storage.cdn_client import CDNClient, ObjectNotFoundError
from infrastructure.storage.presign import get_presign_service
from infrastructure.storage.storage import select_answer_storage


# TODO: delete later, it is not used anymore
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_media_bucket),
) -> Response[ContentUploadedFile]:  # pragma: no cover
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

        key = cdn_client.generate_key(FileScopeEnum.CONTENT, user.id, f"{uuid.uuid4()}/{filename}")
        await cdn_client.upload(key, reader)
    finally:
        for f in to_close:
            f.close()

        for path in to_delete:
            os.remove(path)
    result = ContentUploadedFile(key=key, url=quote(settings.cdn.url.format(key=key), "/:"))
    return Response(result=result)


async def _copy(file: UploadFile, path: str):  # pragma: no cover
    async with aiofiles.open(path, "wb") as fout:
        _size = 1024 * 1024
        while content := await file.read(_size):
            await fout.write(content)


# TODO: delete later, it is not used anymore
async def convert_not_supported_audio(file: UploadFile):  # pragma: no cover
    file.filename = cast(str, file.filename)
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


# TODO: delete later, it is not used, because mobile app does not send heic files, only jpeg.
async def convert_not_supported_image(file: UploadFile):  # pragma: no cover
    file.filename = cast(str, file.filename)
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


def _get_keys_and_bucket_for_image(
    orig_key: str, arb_info: WorkspaceArbitrary | None, cdn_client
) -> tuple[str, str, str]:
    if orig_key.lower().endswith(".heic"):
        target_key = orig_key + ".jpg"
        prefix = f"arbitrary-{arb_info.id}" if arb_info else cdn_client.config.bucket
        upload_key = f"{prefix}/{orig_key}"
        bucket = settings.cdn.bucket_operations
    else:
        target_key = upload_key = orig_key
        bucket = cdn_client.config.bucket
    bucket = cast(str, bucket)
    return target_key, upload_key, bucket


async def download(
    request: FileDownloadRequest = Body(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_media_bucket),
) -> StreamingResponse:
    try:
        file, media_type = cdn_client.download(request.key)
    except ClientError:
        raise SomethingWentWrongError
    except ObjectNotFoundError:
        raise FileNotFoundError

    return StreamingResponse(file, media_type=media_type)


async def answer_upload(
    applet_id: uuid.UUID,
    file_id=Query(None, alias="fileId"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response[AnswerUploadedFile]:
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

        cdn_client = await select_answer_storage(applet_id=applet_id, session=session)
        unique = f"{user.id}/{applet_id}"
        cleaned_file_id = file_id.strip() if file_id else f"{uuid.uuid4()}/{filename}"
        key = cdn_client.generate_key(FileScopeEnum.ANSWER, unique, cleaned_file_id)
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
) -> StreamingResponse:
    cdn_client = await select_answer_storage(applet_id=applet_id, session=session)
    if request.key.startswith(LogFileService.LOG_KEY):
        LogFileService.raise_for_access(user.email)

    try:
        file, media_type = cdn_client.download(request.key)
    except ClientError:
        raise SomethingWentWrongError
    except ObjectNotFoundError:
        raise FileNotFoundError
    return StreamingResponse(file, media_type=media_type)


async def check_file_uploaded(
    applet_id: uuid.UUID,
    schema: FileCheckRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResponseMulti[FileExistenceResponse]:
    """Provides the information if the file is uploaded for an answer."""

    if not await UserAppletAccessCRUD(session).get_by_roles(
        user.id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    ):
        raise AnswerViewAccessDenied()

    cdn_client = await select_answer_storage(applet_id=applet_id, session=session)
    results: list[FileExistenceResponse] = []

    for file_id in schema.files:
        cleaned_file_id = file_id.strip()

        unique = f"{user.id}/{applet_id}"
        orig_key = cdn_client.generate_key(FileScopeEnum.ANSWER, unique, cleaned_file_id)

        file_existence_factory = partial(
            FileExistenceResponse,
            file_id=file_id,
        )

        try:
            await cdn_client.check_existence(orig_key)
            results.append(
                file_existence_factory(
                    uploaded=True,
                    url=cdn_client.generate_private_url(orig_key),
                )
            )
        except NotFoundError:
            results.append(file_existence_factory(uploaded=False))

    return ResponseMulti[FileExistenceResponse](result=results, count=len(results))


async def presign(
    applet_id: uuid.UUID,
    request: FilePresignRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResponseMulti[str | None]:
    service = await get_presign_service(applet_id, user.id, session)
    links = await service.presign(request.private_urls)
    return ResponseMulti[str | None](result=links, count=len(links))  # noqa


async def logs_upload(
    device_id: str,
    file_id: str = Query(..., alias="fileId"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
) -> Response[AnswerUploadedFile]:
    service = LogFileService(user.id, cdn_client)
    try:
        file.filename = cast(str, file.filename)
        key = service.key(device_id=device_id, file_name=file.filename)
        await service.upload(device_id, file, file_id)
        url = await cdn_client.generate_presigned_url(key)
        result = AnswerUploadedFile(key=key, url=url, file_id=file_id)
        await service.backend_log_upload(file_id, True, key)
        return Response(result=result)
    except Exception as ex:
        await service.backend_log_upload(file_id, False, str(ex))
        raise SomethingWentWrongError


async def logs_download(
    device_id: str,
    user_email: str,
    days: int,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
    session: AsyncSession = Depends(get_session),
) -> ResponseMulti[str]:
    UserAccessService.raise_for_developer_access(user.email_encrypted)
    user_service = UserService(session)
    log_user = await user_service.get_by_email(user_email)
    service = LogFileService(log_user.id, cdn_client)
    try:
        end = datetime.datetime.now(tz=pytz.UTC)
        start = end - datetime.timedelta(days=days)
        files = await service.log_list(device_id, start, end)
        futures = []
        for key in map(lambda f: f["Key"], files):
            futures.append(cdn_client.generate_presigned_url(key))
        result = await asyncio.gather(*futures)
        await service.backend_log_download(user.email_encrypted, None, device_id, True)
        return ResponseMulti[str](result=result, count=len(result))
    except Exception as ex:
        await service.backend_log_download(user.email_encrypted, str(ex), device_id, False)
        raise SomethingWentWrongError


async def logs_exist_check(
    device_id: str,
    files: FileCheckRequest,
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
) -> ResponseMulti[LogFileExistenceResponse]:
    service = LogFileService(user.id, cdn_client)
    try:
        result = await service.check_exist(device_id, files.files)
        count = len(result)
        await service.backend_log_check(result, True, None)
        return ResponseMulti[LogFileExistenceResponse](result=result, count=count)
    except Exception as ex:
        await service.backend_log_check([], False, str(ex))
        raise SomethingWentWrongError


async def generate_presigned_media_url(
    body: FileNameRequest = Body(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_media_bucket),
    operations_client: CDNClient = Depends(get_operations_bucket),
) -> Response[PresignedUrl]:
    orig_key = cdn_client.generate_key(FileScopeEnum.CONTENT, user.id, f"{uuid.uuid4()}/{body.file_name}")

    # Webm files go to the operations bucket to be converted to MP4s via Lambda/AWS MediaConvert
    if orig_key.lower().endswith(".webm"):
        extension = body.target_extension if body.target_extension else WebmTargetExtenstion.MP3
        target_key = orig_key + extension
        upload_key = f"{settings.cdn.bucket}/{orig_key}"
        data = operations_client.generate_presigned_post(upload_key)
    else:
        target_key = orig_key
        data = cdn_client.generate_presigned_post(orig_key)

    return Response(
        result=PresignedUrl(
            upload_url=data["url"], fields=data["fields"], url=quote(settings.cdn.url.format(key=target_key), "/:")
        )
    )


async def generate_presigned_answer_url(
    applet_id: uuid.UUID,
    body: FileIdRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response[PresignedUrl]:
    if not await UserAppletAccessCRUD(session).get_by_roles(
        user.id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    ):
        raise AnswerViewAccessDenied()
    cdn_client = await select_answer_storage(applet_id=applet_id, session=session)

    unique = f"{user.id}/{applet_id}"
    cleaned_file_id = body.file_id.strip()

    orig_key = cdn_client.generate_key(FileScopeEnum.ANSWER, unique, cleaned_file_id)
    data = cdn_client.generate_presigned_post(orig_key)

    return Response(
        result=PresignedUrl(
            upload_url=data["url"], fields=data["fields"], url=cdn_client.generate_private_url(orig_key)
        )
    )


async def generate_presigned_logs_url(
    device_id: str,
    body: FileIdRequest = Body(...),
    user: User = Depends(get_current_user),
    cdn_client: CDNClient = Depends(get_log_bucket),
) -> Response[PresignedUrl]:
    service = LogFileService(user.id, cdn_client)
    key = f"{service.device_key_prefix(device_id=device_id)}/{body.file_id}"
    data = cdn_client.generate_presigned_post(key)

    return Response(
        result=PresignedUrl(upload_url=data["url"], fields=data["fields"], url=cdn_client.generate_private_url(key))
    )
