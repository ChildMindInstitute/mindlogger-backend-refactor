import datetime
import re
import uuid
from typing import Dict, List

import pytz
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import config
from apps.file.dependencies import get_legacy_storage
from apps.file.storage import select_storage
from apps.workspaces.constants import StorageType
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service import workspace
from apps.workspaces.service.user_access import UserAccessService
from config import settings
from infrastructure.utility import CDNClient


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


class BasePresignService:
    def __init__(self, session, user_id, applet_id, access):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id
        self.access = access


class S3PresignService(BasePresignService):
    key_pattern = r"s3:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"s3:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = r"s3:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    check_access_to_regular_url_pattern = (
        r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
    )
    check_access_to_legacy_url_pattern = r"\/([0-9a-fA-F]+)\/([0-9a-fA-F]+)\/"

    async def __call__(self, url):
        if not url:
            return
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        arbitary_info = await workspace.WorkspaceService(
            self.session, self.user_id
        ).get_arbitrary_info(self.applet_id)

        legacy_cdn_client = (
            get_legacy_storage() if not arbitary_info else regular_cdn_client
        )

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_key(url)
            return await legacy_cdn_client.generate_presigned_url(key)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_key(url)
            return await regular_cdn_client.generate_presigned_url(key)
        else:
            return url

    def _get_key(self, url):
        pattern = self.key_pattern
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url_format(self, url):
        pattern = self.legacy_file_url_pattern
        match = re.search(pattern, url)
        return bool(match)

    def _is_regular_file_url_format(self, url):
        pattern = self.regular_file_url_pattern
        match = re.search(pattern, url)
        return bool(match)

    async def _check_access_to_regular_url(self, url):
        pattern = self.check_access_to_regular_url_pattern
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if self.user_id == user_id:
            return True

        if str(self.applet_id) != applet_id:
            return False

        if self.access:
            if self.access.role == Role.REVIEWER:
                return user_id in self.access.meta.get("respondents", [])
            return True
        return False

    async def _check_access_to_legacy_url(self, url):
        pattern = self.check_access_to_legacy_url_pattern
        match = re.search(pattern, url)
        applet_id = mongoid_to_uuid(match.group(2))

        if self.applet_id != applet_id:
            return False

        return bool(self.access)


class GCPPresignService(S3PresignService):
    key_pattern = r"gs:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"gs:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = r"gs:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa

    async def __call__(self, url):
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url

        key = self._get_key(url)
        return await regular_cdn_client.generate_presigned_url(key)


class AzurePresignService(GCPPresignService):
    check_access_to_legacy_url_pattern = (
        r"\/[0-9a-fA-F-]+\/([0-9a-fA-F-]+)\/[0-9a-fA-F-]+\/"
    )
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)"

    async def __call__(self, url):
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        key = None

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_legacy_key(url)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_regular_key(url)

        if key is None:
            return url

        return await regular_cdn_client.generate_presigned_url(key)

    def _get_legacy_key(self, url):
        pattern = (
            r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-zA-Z.-]+)$"
        )
        result = re.search(pattern, url)
        return result.group(1)

    def _get_regular_key(self, url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[a-zA-Z0-9.-]+\/[0-9]+)"
        result = re.search(pattern, url)
        return result.group(1)

    def _is_legacy_file_url_format(self, url):
        return (
            ".net/mindlogger/" in url and ".net/mindlogger/answer/" not in url
        )

    def _is_regular_file_url_format(self, url):
        return ".net/mindlogger/answer/" in url


class PresignedUrlsGeneratorService:
    def __init__(
        self, session: AsyncSession, user_id: uuid.UUID, applet_id: uuid.UUID
    ):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id

    async def __call__(
        self,
        *,
        given_private_urls: list[str | None],
    ) -> list[str | None]:
        self.access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            self.applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
        )

        results = await self._generate_presigned_urls(
            given_private_urls=given_private_urls
        )
        return results

    async def _get_service(self):
        arbitary_info = await workspace.WorkspaceService(
            self.session, self.user_id
        ).get_arbitrary_info(self.applet_id)
        if arbitary_info:
            if arbitary_info.storage_type.lower() == StorageType.AZURE.value:
                return AzurePresignService(
                    self.session, self.user_id, self.applet_id, self.access
                )
            if arbitary_info.storage_type.lower() == StorageType.GCP.value:
                return GCPPresignService(
                    self.session, self.user_id, self.applet_id, self.access
                )
        return S3PresignService(
            self.session, self.user_id, self.applet_id, self.access
        )

    async def _generate_presigned_urls(
        self,
        *,
        given_private_urls: list[str | None],
    ):
        urls = list()

        service = await self._get_service()

        for url in given_private_urls:
            url = await service(url)
            urls.append(url)

        return urls


class LogFileService:
    LOG_KEY = "logfiles"

    def __init__(self, user_id: uuid.UUID, cdn: CDNClient):
        self.user_id = user_id
        self.cdn = cdn

    def key(self, device_id: str, file_name: str) -> str:
        ts = str(int(datetime.datetime.utcnow().timestamp()))
        return f"{self.LOG_KEY}/{self.user_id}/{device_id}/{ts}__{file_name}"

    def device_key_prefix(self, device_id: str) -> str:
        return f"{self.LOG_KEY}/{self.user_id}/{device_id}"

    @staticmethod
    def raise_for_access(email: str):
        UserAccessService.raise_for_developer_access(email)

    @staticmethod
    def need_to_rotate(first_file_name: str) -> bool:
        now_ts = datetime.datetime.utcnow()
        file_ts_part = first_file_name.split()[-1:]
        if not file_ts_part:
            return False
        file_ts = datetime.datetime.fromtimestamp(float(file_ts_part[0]))
        return (now_ts - file_ts).days > settings.logs.cycle_days

    async def apply_filo_stack(self, files: List[dict]):
        res = sorted(
            files, key=lambda item: item["LastModified"], reverse=True
        )
        if res:
            oldest_file = res[0]
            date: datetime.datetime = oldest_file["LastModified"]
            now = datetime.datetime.now(tz=pytz.UTC)
            file_date = datetime.datetime.fromtimestamp(
                date.timestamp(), tz=pytz.UTC
            )
            is_out_of_cycle = (
                now - file_date
            ).days > config.settings.logs.cycle_days
            if is_out_of_cycle:
                await self.cdn.delete_object(oldest_file["Key"])
        return res

    async def upload(self, device_id: str, file: UploadFile):
        key = self.device_key_prefix(device_id)
        obj_id = f"{key}/{file.filename}"
        res = await self.cdn.list_object(key)
        res = await self.apply_filo_stack(res)
        await self.cdn.upload(obj_id, file.file)
        return res

    async def log_list(
        self, device_id: str, start: datetime.datetime, end: datetime.datetime
    ):
        def filter_by_interval(file_info: dict) -> bool:
            date_t = file_info["LastModified"]
            date_tz = datetime.datetime.fromtimestamp(
                date_t.timestamp(), tz=pytz.UTC
            )
            return start < date_tz < end

        key = self.device_key_prefix(device_id)
        files = await self.cdn.list_object(key)
        files = sorted(files, key=lambda item: item["LastModified"])
        files = list(filter(filter_by_interval, files))
        return files

    async def check_exist(self, device_id: str, file_names: List[str]):
        key = self.device_key_prefix(device_id)
        file_objects = await self.cdn.list_object(key)
        keys = list(map(lambda f: f["Key"], file_objects))
        result: Dict[str, bool] = dict()
        for file_name in file_names:
            full_id = f"{key}/{file_name}"
            result[file_name] = full_id in keys
        return result
