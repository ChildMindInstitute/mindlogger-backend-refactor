import pytest

from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests import ANSWER_BUCKET_NAME, ANSWER_BUCKET_NAME_DR

FILE_KEY = "/some/file.jpg"


class TestStorageClient:
    @pytest.fixture
    async def answer_storage_client(self, s3_client) -> StorageClient:
        """Regular storage client"""
        config = StorageConfig(
            endpoint_url=None,
            region="us-east-1",
            bucket=ANSWER_BUCKET_NAME,
        )
        client = StorageClient(config, env="test")
        client.client = s3_client

        return client

    @pytest.fixture
    async def answer_storage_client_dr(self, s3_client) -> StorageClient:
        """Storage client configured for DR"""
        config = StorageConfig(
            endpoint_url=None, region="us-east-1", bucket=ANSWER_BUCKET_NAME, bucket_override=ANSWER_BUCKET_NAME_DR
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

    async def test_generate_presigned_post(self, answer_storage_client):
        data = answer_storage_client.generate_presigned_post(FILE_KEY)
        assert data is not None
        assert ANSWER_BUCKET_NAME in data["url"]
        assert ANSWER_BUCKET_NAME_DR not in data["url"]

    async def test_generate_presigned_post_dr(self, answer_storage_client_dr):
        data = answer_storage_client_dr.generate_presigned_post(FILE_KEY)
        assert data is not None
        assert ANSWER_BUCKET_NAME_DR in data["url"]

    async def test_generate_presigned_url(self, answer_storage_client):
        data = await answer_storage_client.generate_presigned_url(FILE_KEY)
        assert data is not None
        assert ANSWER_BUCKET_NAME in data
        assert ANSWER_BUCKET_NAME_DR not in data

    async def test_generate_presigned_url_dr(self, answer_storage_client_dr):
        data = await answer_storage_client_dr.generate_presigned_url(FILE_KEY)
        assert data is not None
        assert ANSWER_BUCKET_NAME_DR in data

    @pytest.mark.usefixtures("populate_s3")
    async def test_check_existence(self, answer_storage_client: StorageClient):
        await answer_storage_client.check_existence(FILE_KEY)
