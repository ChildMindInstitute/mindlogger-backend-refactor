import pytest

from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests import ANSWER_BUCKET_NAME

FILE_KEY = "/some/file.jpg"


class TestStorageClient:
    @pytest.fixture
    async def answer_storage_client(self, s3_client) -> StorageClient:
        config = StorageConfig(
            endpoint_url=None,
            region="us-east-1",
            bucket=ANSWER_BUCKET_NAME,
        )
        client = StorageClient(config, env="test")
        client.client = s3_client

        return client

    @pytest.fixture
    async def populate_s3(self, answer_bucket):
        answer_bucket.put_object(
            Body=b"this is a file",
            Key=FILE_KEY,
        )

    @pytest.mark.usefixtures("populate_s3")
    async def test_get_answer_storage_client(self, answer_storage_client: StorageClient):
        await answer_storage_client.check_existence(FILE_KEY)
