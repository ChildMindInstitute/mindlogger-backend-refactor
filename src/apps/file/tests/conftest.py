from typing import Any, Generator

import pytest

from apps.file.tests import FILE_KEY, MEDIA_BUCKET_NAME, MEDIA_BUCKET_NAME_DR, MEDIA_STORAGE_ADDRESS
from config import CDNSettings, settings
from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests import ANSWER_BUCKET_NAME, ANSWER_BUCKET_NAME_DR
from infrastructure.storage.tests.conftest import answer_bucket, aws_credentials, s3_client, s3_resource

__all__ = [
    "aws_credentials",
    "s3_client",
    "s3_resource",
    "answer_bucket",
    "ANSWER_BUCKET_NAME",
    "ANSWER_BUCKET_NAME_DR",
    "answer_storage_client",
    "answer_storage_client_dr",
    "populate_s3",
]


@pytest.fixture
async def answer_storage_client(s3_client) -> StorageClient:
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
async def answer_storage_client_dr(s3_client) -> StorageClient:
    """Storage client configured for DR"""
    config = StorageConfig(
        endpoint_url=None, region="us-east-1", bucket=ANSWER_BUCKET_NAME, bucket_override=ANSWER_BUCKET_NAME_DR
    )

    client = StorageClient(config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def media_storage_client_dr(s3_client) -> StorageClient:
    """Storage client configured for DR"""
    config = StorageConfig(
        endpoint_url=MEDIA_STORAGE_ADDRESS,
        region="us-east-1",
        bucket=MEDIA_BUCKET_NAME,
        bucket_override=MEDIA_BUCKET_NAME_DR,
    )

    client = StorageClient(config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def populate_s3(answer_bucket):
    answer_bucket.put_object(
        Body=b"this is a file",
        Key=FILE_KEY,
    )


@pytest.fixture
def cdn_settings() -> Generator[CDNSettings, Any, None]:
    # TODO This fixture is leaky.  Might be a better fix in the future
    yield settings.cdn

    # settings.cdn.access_key = "access_key"
    # settings.cdn.secret_key = "secret_key"
    # settings.cdn.bucket = "bucket"
    # settings.cdn.bucket_answer = "bucket_answer"
    # settings.cdn.bucket_operations = "bucket_operations"
    # settings.cdn.region = "us-east-1"
    # settings.cdn.domain = "mindlogger"
    # settings.cdn.legacy_prefix = "mindlogger/legacy-answer"
    # yield settings.cdn
    # settings.cdn.bucket_operations = None
    # settings.cdn.access_key = None
    # settings.cdn.secret_key = None
    # settings.cdn.bucket = None
    # settings.cdn.bucket_answer = None
    # settings.cdn.region = None
    # settings.cdn.domain = ""
    # settings.cdn.legacy_prefix = None
