import json
import uuid
from io import BytesIO

from apps.file.enums import FileScopeEnum
from apps.file.storage import select_storage
from apps.integrations.oneup_health.service.domain import EHRData


class EHRStorage:
    def __init__(self, session, applet_id: uuid.UUID):
        self.session = session
        self.applet_id = applet_id

    def get_unique_path(self, data: EHRData):
        return f"{data.unique_id}/{data.date.strftime('%Y-%m-%d')}/{data.healthcare_provider_id}"

    async def upload(self, data: EHRData):
        cdn_client = await select_storage(applet_id=self.applet_id, session=self.session)
        unique = self.get_unique_path(data)
        filename = "resources.json"
        key = cdn_client.generate_key(FileScopeEnum.EHR, unique, filename)

        # Serialize to JSON and encode to bytes
        json_data = json.dumps(data.resources)
        bytes_data = json_data.encode("utf-8")

        # Create a binary stream
        binary_data = BytesIO(bytes_data)

        await cdn_client.upload(key, binary_data)

        return
