import pytest

from config import CDNSettings
from infrastructure.storage.storage_config import StorageConfig


def test_generate_media_settings():
    cdn_settings = CDNSettings(
        domain="media.example.com",
        bucket="media-bucket",
        bucket_override="media-override",
        region="us-east-1",
        secret_key="secret",
        access_key="access",
        ttl_signed_urls=7200,
        bucket_kms_enabled=True,
        bucket_kms_key_id="kms-key-id",
    )
    config = StorageConfig.generate_media_settings(cdn_settings)

    assert config.domain == "media.example.com"
    assert config.bucket == "media-bucket"
    assert config.bucket_override == "media-override"
    assert config.region == "us-east-1"
    assert config.secret_key == "secret"
    assert config.access_key == "access"
    assert config.ttl_signed_urls == 7200
    assert config.kms_enabled is True
    assert config.kms_key_id == "kms-key-id"


def test_generate_answer_settings():
    cdn_settings = CDNSettings(
        bucket_answer="answer-bucket",
        bucket_answer_override="answer-override",
        region="us-east-1",
        secret_key="secret",
        access_key="access",
        ttl_signed_urls=3600,
        bucket_answer_kms_enabled=True,
        bucket_answer_kms_key_id="answer-kms-key",
    )
    config = StorageConfig.generate_answer_settings(cdn_settings)

    assert config.bucket == "answer-bucket"
    assert config.bucket_override == "answer-override"
    assert config.region == "us-east-1"
    assert config.secret_key == "secret"
    assert config.access_key == "access"
    assert config.ttl_signed_urls == 3600
    assert config.kms_enabled is True
    assert config.kms_key_id == "answer-kms-key"


def test_generate_answer_settings_with_kms_missing(normal_storage_settings: CDNSettings):
    with pytest.raises(ValueError):
        CDNSettings(
            bucket_answer="answer-bucket",
            bucket_answer_override="answer-override",
            region="us-east-1",
            secret_key="secret",
            access_key="access",
            ttl_signed_urls=3600,
            bucket_answer_kms_enabled=True,
            bucket_answer_kms_key_id=None,
        )

    with pytest.raises(ValueError):
        StorageConfig(
            endpoint_url=None,
            region="us-east-1",
            bucket="asdf",
            kms_enabled=True,
            kms_key_id=None,
        )


def test_generate_operations_settings():
    cdn_settings = CDNSettings(
        bucket_operations="ops-bucket",
        bucket_operation_override="ops-override",
        region="us-east-1",
        secret_key="secret",
        access_key="access",
        ttl_signed_urls=1800,
        bucket_operation_kms_enabled=False,
        bucket_operation_kms_key_id=None,
    )
    config = StorageConfig.generate_operations_settings(cdn_settings)

    assert config.bucket == "ops-bucket"
    assert config.bucket_override == "ops-override"
    assert config.region == "us-east-1"
    assert config.secret_key == "secret"
    assert config.access_key == "access"
    assert config.ttl_signed_urls == 1800
    assert config.kms_enabled is False
    assert config.kms_key_id is None


def test_generate_logs_settings():
    cdn_settings = CDNSettings(
        bucket_answer="logs-bucket",
        bucket_answer_override="logs-override",
        region="us-east-1",
        secret_key="secret",
        access_key="access",
        ttl_signed_urls=3600,
    )
    config = StorageConfig.generate_logs_settings(cdn_settings)

    assert config.bucket == "logs-bucket"
    assert config.bucket_override == "logs-override"
    assert config.region == "us-east-1"
    assert config.secret_key == "secret"
    assert config.access_key == "access"
    assert config.ttl_signed_urls == 3600
    # KMS settings are not set in generate_logs_settings
    assert config.kms_enabled is False
    assert config.kms_key_id is None


def test_storage_config_defaults():
    config = StorageConfig()
    assert config.endpoint_url is None
    assert config.region is None
    assert config.bucket is None
    assert config.secret_key is None
    assert config.access_key is None
    assert config.kms_enabled is False
    assert config.kms_key_id is None
    assert config.domain == ""
    assert config.storage_address is None
    assert config.ttl_signed_urls == 3600
    assert config.bucket_override is None
