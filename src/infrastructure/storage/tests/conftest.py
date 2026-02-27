import os

import boto3
import pytest
from moto import mock_aws

from config import CDNSettings, Settings, settings
from infrastructure.storage.storage_config import StorageConfig
from infrastructure.storage.tests import (
    ANSWER_BUCKET_NAME,
    ANSWER_OVERRIDE,
    DOMAIN,
    MEDIA_BUCKET_NAME,
    MEDIA_OVERRIDE,
    OPERATIONS_BUCKET_NAME,
    OPERATIONS_OVERRIDE,
)


@pytest.fixture(scope="function")
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
async def s3_client(aws_credentials):
    """
    Return a mocked S3 client
    """
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


# @pytest.fixture(scope="function")
# async def mocked_aws(aws_credentials):
#     """
#     Mock all AWS interactions
#     Requires you to create your own boto3 clients
#     """
#     with mock_aws():
#         yield


@pytest.fixture(scope="function")
def s3_resource():
    with mock_aws():
        s3 = boto3.resource("s3", region_name="us-east-1")
        yield s3


@pytest.fixture(scope="function")
def answer_bucket(s3_resource):
    """Create the bucket in Moto"""
    bucket = s3_resource.create_bucket(Bucket=ANSWER_BUCKET_NAME)
    bucket.create()
    yield bucket


@pytest.fixture
async def normal_storage_settings() -> Settings:
    """Settings for prod-like storage"""
    normal = settings.model_copy(deep=True)
    cdn_settings = CDNSettings(
        domain=DOMAIN,
        bucket=MEDIA_BUCKET_NAME,
        bucket_answer=ANSWER_BUCKET_NAME,
        bucket_operations=OPERATIONS_BUCKET_NAME,
        region="us-east-1",
        ttl_signed_urls=3600,
    )

    normal.cdn = cdn_settings

    return normal


@pytest.fixture
async def local_storage_settings() -> Settings:
    """Settings for local with minio storage"""
    normal = settings.model_copy(deep=True)
    cdn_settings = CDNSettings(
        bucket=MEDIA_BUCKET_NAME,
        bucket_answer=ANSWER_BUCKET_NAME,
        bucket_operations=OPERATIONS_BUCKET_NAME,
        region="us-east-1",
        ttl_signed_urls=3600,
        endpoint_url="http://localhost:9000",
        storage_address=f"http://localhost:9000/{MEDIA_BUCKET_NAME}",
    )
    normal.cdn = cdn_settings

    return normal


@pytest.fixture
async def cdn_override_settings(normal_storage_settings: Settings) -> Settings:
    """Settings for DR"""
    dr_settings = normal_storage_settings.model_copy(deep=True)
    dr_settings.cdn.bucket_override = MEDIA_OVERRIDE
    dr_settings.cdn.bucket_operation_override = OPERATIONS_OVERRIDE
    dr_settings.cdn.bucket_answer_override = ANSWER_OVERRIDE

    return dr_settings


@pytest.fixture
async def media_storage_config(normal_storage_settings: Settings) -> StorageConfig:
    """Settings for storage"""
    config = StorageConfig(
        endpoint_url=None,
        domain=normal_storage_settings.cdn.domain,
        region="us-east-1",
        bucket=normal_storage_settings.cdn.bucket,
        access_key=normal_storage_settings.cdn.access_key,
        secret_key=normal_storage_settings.cdn.secret_key,
    )

    return config


@pytest.fixture
async def answer_storage_config(normal_storage_settings: Settings) -> StorageConfig:
    """Settings for storage"""
    config = StorageConfig(
        endpoint_url=None,
        region="us-east-1",
        bucket=normal_storage_settings.cdn.bucket_answer,
        access_key=normal_storage_settings.cdn.access_key,
        secret_key=normal_storage_settings.cdn.secret_key,
    )

    return config


@pytest.fixture
async def operations_storage_config(normal_storage_settings: Settings) -> StorageConfig:
    """Settings for storage"""
    config = StorageConfig(
        endpoint_url=None,
        region="us-east-1",
        bucket=normal_storage_settings.cdn.bucket_operations,
        access_key=normal_storage_settings.cdn.access_key,
        secret_key=normal_storage_settings.cdn.secret_key,
    )

    return config
