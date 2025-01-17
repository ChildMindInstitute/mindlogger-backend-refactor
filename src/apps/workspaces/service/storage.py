import uuid


class ArbitraryStorage:
    def __init__(
        self,
        workspace_id: uuid.UUID,
        access_key: str,
        secret_key: str,
        region: str,
    ):
        self.workspace_id = workspace_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.client = None

    def _get_full_path(self, applet_id: uuid.UUID, activity_id: uuid.UUID) -> str:
        return f"{self.workspace_id}/{applet_id}/{activity_id}/{self._get_filename()}"

    def _get_filename(self) -> str:
        return "filename"

    def upload(self, applet_id: uuid.UUID, activity_id: uuid.UUID):
        raise Exception("Not implemented")


class S3Storage(ArbitraryStorage):
    def __init__(self):
        pass
