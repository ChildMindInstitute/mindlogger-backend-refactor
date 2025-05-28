import asyncio
import datetime
import uuid
from logging import ERROR, INFO
from typing import List

import pytz
from fastapi import UploadFile

import config
from apps.file.domain import LogFileExistenceResponse
from apps.workspaces.service.user_access import UserAccessService
from config import settings
from infrastructure.logger import logger
from infrastructure.utility import CDNClient


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
