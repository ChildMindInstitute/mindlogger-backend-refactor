import io
import json
import os
import uuid
import zipfile
from io import BytesIO

from slugify import slugify
from typing_extensions import BinaryIO

from apps.file.enums import FileScopeEnum
from apps.integrations.oneup_health.service.domain import EHRData
from infrastructure.storage.cdn_client import CDNClient
from infrastructure.storage.storage import select_answer_storage

__all = ["create_ehr_storage"]


class EHRStorage:
    def __init__(self, cdn_client: CDNClient):
        self._cdn_client: CDNClient = cdn_client

    def _get_storage_path(self, base_path: str, key: str) -> str:
        index = key.find(base_path)
        if index == -1:  # substring not found
            return key

        # Return everything up to and including the unique substring
        return key[: index + len(base_path)]

    async def upload_resources(self, data: EHRData) -> tuple[str, str]:
        base_path = f"{data.activity_id}/{data.submit_id}"
        provider_name = (
            slugify(data.healthcare_provider_name, separator="_")
            if data.healthcare_provider_name
            else data.healthcare_provider_id
        )
        filename = f"{data.user_id}-{data.date.strftime('%Y%m%d')}-{provider_name}.json"
        key = self._cdn_client.generate_key(FileScopeEnum.EHR, base_path, filename)

        # Serialize to JSON and encode to bytes
        json_data = json.dumps(data.resources)
        bytes_data = json_data.encode("utf-8")

        # Create a binary stream
        binary_data = BytesIO(bytes_data)

        await self._cdn_client.upload(key, binary_data)

        return self._get_storage_path(base_path, key), filename

    async def upload_ehr_zip(self, resources_files: list[str], data: EHRData) -> str:
        base_path = f"{data.activity_id}/{data.submit_id}"
        filename = f"{data.user_id}-{data.activity_id}-{data.submit_id}-{data.date.strftime('%Y%m%d')}-EHR.zip"
        key = self._cdn_client.generate_key(FileScopeEnum.EHR, base_path, filename)

        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                for resource_file in resources_files:
                    file_buffer = io.BytesIO()

                    self._cdn_client.download(resource_file, file_buffer)
                    file_buffer.seek(0)

                    # Use the resource_file as the filename inside the zip
                    # Extract just the filename part if resource_file contains a path
                    resource_filename = os.path.basename(resource_file)
                    zip_file.writestr(resource_filename, file_buffer.getvalue())
                    file_buffer.close()

            zip_buffer.seek(0)
            await self._cdn_client.upload(key, zip_buffer)
            return key
        finally:
            zip_buffer.close()

    def download_ehr_zip(self, data: EHRData, file_buffer: BinaryIO) -> str:
        base_path = f"{data.activity_id}/{data.submit_id}"
        filename = f"{data.user_id}-{data.activity_id}-{data.submit_id}-{data.date.strftime('%Y%m%d')}-EHR.zip"
        key = self._cdn_client.generate_key(FileScopeEnum.EHR, base_path, filename)

        self._cdn_client.download(key, file_buffer)

        return filename


async def create_ehr_storage(session, applet_id: uuid.UUID):
    cdn_client = await select_answer_storage(applet_id=applet_id, session=session)

    return EHRStorage(cdn_client)
