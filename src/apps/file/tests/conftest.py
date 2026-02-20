import pytest
from fastapi import FastAPI

from apps.file.tests import FILE_KEY
from config import CDNSettings, Settings, get_settings
from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests.conftest import (
    answer_bucket,
    aws_credentials,
    cdn_override_settings,
    normal_storage_settings,
    s3_client,
    s3_resource,
)

# This does nothing, but it fakes out ruff to leave the imported fixtures from other packages
__all__ = [
    "aws_credentials",
    "s3_client",
    "s3_resource",
    "answer_bucket",
    "answer_storage_client",
    "answer_storage_client_dr",
    "populate_s3",
    "cdn_override_settings",
    "normal_storage_settings",
]


@pytest.fixture
async def answer_storage_client(s3_client, answer_storage_config) -> StorageClient:
    """Regular storage client"""
    client = StorageClient(answer_storage_config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def answer_storage_client_dr(s3_client, cdn_override_settings: Settings) -> StorageClient:
    """Storage client configured for DR"""
    config = StorageConfig(
        endpoint_url=None,
        region="us-east-1",
        bucket=cdn_override_settings.cdn.bucket_answer,
        bucket_override=cdn_override_settings.cdn.bucket_answer_override,
    )

    client = StorageClient(config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def media_storage_client(s3_client, media_storage_config) -> StorageClient:
    """Regular storage client"""
    client = StorageClient(media_storage_config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def media_storage_config_dr(s3_client, cdn_override_settings: Settings) -> StorageConfig:
    config = StorageConfig(
        endpoint_url=None,
        domain=cdn_override_settings.cdn.domain,
        region="us-east-1",
        bucket=cdn_override_settings.cdn.bucket,
        bucket_override=cdn_override_settings.cdn.bucket_override,
    )

    return config


@pytest.fixture
async def media_storage_client_dr(s3_client, media_storage_config_dr: StorageConfig) -> StorageClient:
    """Storage client configured for DR"""
    client = StorageClient(media_storage_config_dr, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def operations_storage_client(s3_client, operations_storage_config) -> StorageClient:
    """Regular storage client"""
    client = StorageClient(operations_storage_config, env="test")
    client.client = s3_client

    return client


@pytest.fixture
async def operations_storage_client_dr(s3_client, cdn_override_settings: Settings) -> StorageClient:
    """Storage client configured for DR"""
    config = StorageConfig(
        endpoint_url=cdn_override_settings.cdn.endpoint_url,
        region="us-east-1",
        bucket=cdn_override_settings.cdn.bucket_override,
        bucket_override=cdn_override_settings.cdn.bucket_operation_override,
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
def override_app_settings(app: FastAPI, normal_storage_settings: Settings):
    """Override app CDN settings from .env with known good settings for tests"""
    def new_get_settings():
        return normal_storage_settings

    app.dependency_overrides[get_settings] = new_get_settings
    yield
    app.dependency_overrides.pop(get_settings)


@pytest.fixture
def cdn_settings(normal_storage_settings: Settings) -> CDNSettings:
    # TODO This fixture is leaky.  Might be a better fix in the future
    return normal_storage_settings.cdn
