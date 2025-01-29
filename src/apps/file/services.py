import asyncio
import datetime
import re
import uuid
from logging import ERROR, INFO
from typing import List

import pytz
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import config
from apps.file.domain import LogFileExistenceResponse
from apps.file.storage import select_storage
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import WorkspaceArbitrary
from apps.workspaces.service import workspace
from apps.workspaces.service.user_access import UserAccessService
from config import settings
from infrastructure.dependency.cdn import get_legacy_bucket
from infrastructure.logger import logger
from infrastructure.utility import CDNClient


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


class S3PresignService:
    key_pattern = r"s3:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"s3:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = (
        r"s3:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    )
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
    check_access_to_legacy_url_pattern = r"\/([0-9a-fA-F]+)\/([0-9a-fA-F]+)\/"

    def __init__(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        access: UserAppletAccessSchema | None,
    ):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id
        self.access = access

    async def get_regular_client(self) -> CDNClient:
        return await select_storage(applet_id=self.applet_id, session=self.session)

    async def get_legacy_client(self, info: WorkspaceArbitrary | None) -> CDNClient:
        if not info:
            return await get_legacy_bucket()
        else:
            return await self.get_regular_client()

    async def _presign(self, url: str | None, legacy_cdn_client: CDNClient, regular_cdn_client: CDNClient):
        if not url:
            return

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_key(url)
            if legacy_cdn_client.is_bucket_public() or await legacy_cdn_client.is_object_public(key):
                return await legacy_cdn_client.generate_public_url(key)
            return await legacy_cdn_client.generate_presigned_url(key)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_key(url)
            return await regular_cdn_client.generate_presigned_url(key)
        else:
            return url

    async def presign(self, urls: List[str | None]) -> List[str]:
        c_list = []
        wsp_service = workspace.WorkspaceService(self.session, self.user_id)
        arbitrary_info = await wsp_service.get_arbitrary_info_if_use_arbitrary(self.applet_id)
        legacy_cdn_client = await self.get_legacy_client(arbitrary_info)
        regular_cdn_client = await self.get_regular_client()

        for url in urls:
            c_list.append(self._presign(url, legacy_cdn_client, regular_cdn_client))
        result = await asyncio.gather(*c_list)
        return result

    def _get_key(self, url):
        pattern = self.key_pattern
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url_format(self, url):
        match = re.search(self.legacy_file_url_pattern, url)
        return bool(match)

    def _is_regular_file_url_format(self, url):
        match = re.search(self.regular_file_url_pattern, url)
        return bool(match)

    async def _check_access_to_regular_url(self, url):
        pattern = self.check_access_to_regular_url_pattern
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if self.user_id == user_id:
            return True

        if str(self.applet_id) != applet_id:
            return False

        if self.access and self.access.role != Role.RESPONDENT:
            return True

        return False

    async def _check_access_to_legacy_url(self, url):
        pattern = self.check_access_to_legacy_url_pattern
        match = re.search(pattern, url)
        if not match:
            return False
        applet_id = mongoid_to_uuid(match.group(2))

        if self.applet_id != applet_id:
            return False

        return bool(self.access)


class GCPPresignService(S3PresignService):
    key_pattern = r"gs:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"gs:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = (
        r"gs:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    )

    async def _presign(self, url: str | None, *kwargs):
        regular_cdn_client = await select_storage(applet_id=self.applet_id, session=self.session)

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url

        key = self._get_key(url)
        return await regular_cdn_client.generate_presigned_url(key)


class AzurePresignService(GCPPresignService):
    check_access_to_legacy_url_pattern = r"\/[0-9a-fA-F-]+\/([0-9a-fA-F-]+)\/[0-9a-fA-F-]+\/"
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)"

    async def __call__(self, url):
        regular_cdn_client = await select_storage(applet_id=self.applet_id, session=self.session)
        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_legacy_key(url)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_regular_key(url)
        else:
            return url
        return await regular_cdn_client.generate_presigned_url(key)

    def _get_legacy_key(self, url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-zA-Z.-]+)$"
        result = re.search(pattern, url)
        return result.group(1)

    def _get_regular_key(self, url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[a-zA-Z0-9.-]+\/[0-9]+)"
        result = re.search(pattern, url)
        return result.group(1)

    def _is_legacy_file_url_format(self, url):
        return ".net/mindlogger/" in url and ".net/mindlogger/answer/" not in url

    def _is_regular_file_url_format(self, url):
        return ".net/mindlogger/answer/" in url


class LogFileService:
    LOG_KEY = "logfiles"
    BE_LOG_PREFIX = "LOGFILE"
    BE_LOG_LEVEL = INFO
    METHOD_UPLOAD = "logs-upload"
    METHOD_CHECK = "logs-upload-check"
    METHOD_DOWNLOAD = "logs-download"

    def __init__(self, user_id: uuid.UUID, cdn: CDNClient):
        self.user_id = user_id
        self.cdn = cdn

    def key(self, device_id: str, file_name: str) -> str:
        return f"{self.LOG_KEY}/{self.user_id}/{device_id}/{file_name}"

    def device_key_prefix(self, device_id: str) -> str:
        return f"{self.LOG_KEY}/{self.user_id}/{device_id}"

    @staticmethod
    def raise_for_access(email: str):
        UserAccessService.raise_for_developer_access(email)

    @staticmethod
    def need_to_rotate(first_file_name: str) -> bool:
        now_ts = datetime.datetime.now(datetime.UTC)
        file_ts_part = first_file_name.split()[-1:]
        if not file_ts_part:
            return False
        file_ts = datetime.datetime.fromtimestamp(float(file_ts_part[0]))
        return (now_ts - file_ts).days > settings.logs.cycle_days

    async def apply_filo_stack(self, files: List[dict]):
        res = sorted(files, key=lambda item: item["LastModified"], reverse=True)
        if res:
            oldest_file = res[0]
            date: datetime.datetime = oldest_file["LastModified"]
            now = datetime.datetime.now(tz=pytz.UTC)
            file_date = datetime.datetime.fromtimestamp(date.timestamp(), tz=pytz.UTC)
            is_out_of_cycle = (now - file_date).days > config.settings.logs.cycle_days
            if is_out_of_cycle:
                await self.cdn.delete_object(oldest_file["Key"])
        return res

    async def upload(self, device_id: str, file: UploadFile, file_id: str):
        key = self.device_key_prefix(device_id)
        obj_id = f"{key}/{file_id}"
        res = await self.cdn.list_object(key)
        res = await self.apply_filo_stack(res)
        await self.cdn.upload(obj_id, file.file)
        return res

    async def log_list(self, device_id: str, start: datetime.datetime, end: datetime.datetime):
        def filter_by_interval(file_info: dict) -> bool:
            date_t = file_info["LastModified"]
            date_tz = datetime.datetime.fromtimestamp(date_t.timestamp(), tz=pytz.UTC)
            return start < date_tz < end

        key = self.device_key_prefix(device_id)
        files = await self.cdn.list_object(key)
        files = sorted(files, key=lambda item: item["Key"], reverse=True)
        files = list(filter(filter_by_interval, files))
        return files

    async def check_exist(self, device_id: str, file_names: List[str]) -> list[LogFileExistenceResponse]:
        key = self.device_key_prefix(device_id)
        file_objects = await self.cdn.list_object(key)
        result: list[LogFileExistenceResponse] = []
        for file_name in file_names:
            prefix = key[:]
            full_id = f"{prefix}/{file_name}"
            file_flt = filter(lambda f: f["Key"] == full_id, file_objects)
            file_object: dict = next(file_flt, {})
            file_key = self.key(device_id=device_id, file_name=file_name)
            if file_object:
                url = await self.cdn.generate_presigned_url(file_key)
                file_id = file_name
            else:
                url = None
                file_id = file_name
            result.append(
                LogFileExistenceResponse(
                    key=file_key,
                    uploaded=bool(file_object),
                    url=url,
                    file_id=file_id,
                    file_size=file_object.get("Size"),
                )
            )
        return result

    async def backend_log(self, method_name: str, details: dict, success: bool):
        logger.log(
            self.BE_LOG_LEVEL if success else ERROR,
            f"{self.BE_LOG_PREFIX} - {method_name}: {details}",
        )

    async def backend_log_upload(self, file_id: str, success: bool, details: str | None):
        row = {
            "userId": str(self.user_id),
            "fileId": str(file_id),
            "success": "true" if success else "false",
            "details": details,
        }
        await self.backend_log(self.METHOD_UPLOAD, row, success)

    async def backend_log_check(
        self,
        files: list[LogFileExistenceResponse],
        success: bool,
        details: str | None,
    ):
        row = {
            "userId": str(self.user_id),
            "response": [file.dict() for file in files],
            "success": "true" if success else "false",
            "details": details,
        }
        await self.backend_log(self.METHOD_CHECK, row, success)

    async def backend_log_download(
        self,
        email: str | None,
        details: str | None,
        device_id: str,
        success: bool,
    ):
        row = {
            "userId": str(self.user_id),
            "deviceId": device_id,
            "success": "true" if success else "false",
            "email": email,
            "details": details,
        }
        await self.backend_log(self.METHOD_CHECK, row, success)
