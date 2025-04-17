import json
import uuid
from io import BytesIO

from apps.file.enums import FileScopeEnum
from apps.file.storage import select_storage
from apps.integrations.oneup_health.service.domain import EHRData
from infrastructure.utility import CDNClient

__all = ["create_ehr_storage"]


class _EHRStorage:
    def __init__(self, session, applet_id: uuid.UUID, cdn_client: CDNClient):
        self._session = session
        self._applet_id = applet_id
        self._cdn_client: CDNClient = cdn_client

    def _get_storage_path(self, base_path: str, key: str) -> str:
        index = key.find(base_path)
        if index == -1:  # substring not found
            return key

        # Return everything up to and including the unique substring
        return key[: index + len(base_path)]

    async def upload_resources(self, data: EHRData):
        base_path = f"{data.unique_id}/{data.date.strftime('%Y-%m-%d')}"
        filename = "resources.json"
        key = self._cdn_client.generate_key(FileScopeEnum.EHR, f"{base_path}/{data.healthcare_provider_id}", filename)

        # Serialize to JSON and encode to bytes
        json_data = json.dumps(data.resources)
        bytes_data = json_data.encode("utf-8")

        # Create a binary stream
        binary_data = BytesIO(bytes_data)

        await self._cdn_client.upload(key, binary_data)

        return self._get_storage_path(base_path, key)


async def create_ehr_storage(session, applet_id: uuid.UUID):
    cdn_client = await select_storage(applet_id=applet_id, session=session)

    return _EHRStorage(session, applet_id, cdn_client)
