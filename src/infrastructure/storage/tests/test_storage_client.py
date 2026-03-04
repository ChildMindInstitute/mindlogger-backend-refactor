import pytest

from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests import ANSWER_BUCKET_NAME, ANSWER_OVERRIDE, MEDIA_BUCKET_NAME

FILE_KEY = "/some/file.jpg"
DOMAIN = "test.gettingcurious.com"
ENDPOINT_URL = "http://localhost:9999"
STORAGE_ADDRESS = f"{ENDPOINT_URL}/{MEDIA_BUCKET_NAME}"


class TestStorageClient:
    """Test for StorageClient implementation details"""

    @pytest.fixture
    async def answer_storage_client(self, s3_client) -> StorageClient:
        """Regular storage client"""
        config = StorageConfig(
            endpoint_url=None,
            region="us-east-1",
            bucket=ANSWER_BUCKET_NAME,
            domain=DOMAIN,
        )
        client = StorageClient(config, env="test")
        client.client = s3_client

        return client

    @pytest.fixture
    async def media_storage_client_other(self, s3_client) -> StorageClient:
        """Regular storage client with local type settings"""
        config = StorageConfig(
            endpoint_url=ENDPOINT_URL,
            region="us-east-1",
            bucket=ANSWER_BUCKET_NAME,
            storage_address=STORAGE_ADDRESS,
        )
        client = StorageClient(config, env="test")
        client.client = s3_client

        return client

    @pytest.fixture
    async def answer_storage_client_dr(self, s3_client) -> StorageClient:
        """Storage client configured for DR"""
        config = StorageConfig(
            endpoint_url=None, region="us-east-1", bucket=ANSWER_BUCKET_NAME, bucket_override=ANSWER_OVERRIDE
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
        assert ANSWER_OVERRIDE not in data["url"]

    async def test_generate_presigned_post_dr(self, answer_storage_client_dr):
        data = answer_storage_client_dr.generate_presigned_post(FILE_KEY)
        assert data is not None
        assert ANSWER_OVERRIDE in data["url"]

    async def test_generate_presigned_url(self, answer_storage_client):
        data = await answer_storage_client.generate_presigned_url(FILE_KEY)
        assert data is not None
        assert ANSWER_BUCKET_NAME in data
        assert ANSWER_OVERRIDE not in data

    async def test_generate_presigned_url_dr(self, answer_storage_client_dr):
        data = await answer_storage_client_dr.generate_presigned_url(FILE_KEY)
        assert data is not None
        assert ANSWER_OVERRIDE in data

    @pytest.mark.usefixtures("populate_s3")
    async def test_check_existence(self, answer_storage_client: StorageClient):
        await answer_storage_client.check_existence(FILE_KEY)

    async def test_invalid_public_url_config(self):
        client = StorageClient(config=StorageConfig(), env="test")
        with pytest.raises(ValueError):
            client.generate_public_url("foo.jpg")

    async def test_get_public_url(self, answer_storage_client: StorageClient):
        url = answer_storage_client.generate_public_url(FILE_KEY)
        assert DOMAIN in url
        assert FILE_KEY in url

    async def test_get_public_url_other_storage_address(self, media_storage_client_other: StorageClient):
        url = media_storage_client_other.generate_public_url(FILE_KEY)
        assert DOMAIN not in url
        assert STORAGE_ADDRESS in url
        assert FILE_KEY in url
