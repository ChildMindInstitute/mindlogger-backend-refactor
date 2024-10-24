from contextlib import suppress
from datetime import datetime, timedelta
from typing import BinaryIO

import boto3
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas
from botocore.config import Config

from infrastructure.utility.cdn_client import CDNClient
from infrastructure.utility.cdn_config import CdnConfig


class ArbitraryS3CdnClient(CDNClient):
    def configure_client(self, config: CdnConfig, signature_version=None):
        client_config = Config(
            max_pool_connections=25,
        )
        return boto3.client(
            "s3",
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region,
            config=client_config,
        )


class ArbitraryGCPCdnClient(CDNClient):
    def __init__(self, config: CdnConfig, endpoint_url: str, env: str, *, max_concurrent_tasks: int = 10):
        self.endpoint_url = endpoint_url
        super().__init__(config, env)

    def generate_private_url(self, key):
        return f"gs://{self.config.bucket}/{key}"

    def configure_client(self, config, signature_version=None):
        client_config = Config(
            max_pool_connections=25,
        )
        return boto3.client(
            "s3",
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region,
            endpoint_url=self.endpoint_url,
            config=client_config,
        )


class ArbitraryAzureCdnClient(CDNClient):
    def __init__(self, sec_key: str, bucket: str, env: str = "", *, max_concurrent_tasks: int = 10):
        self.sec_key = sec_key
        super().__init__(CdnConfig(bucket=bucket), env)

    @classmethod
    def generate_key(cls, scope, unique, filename):
        return f"{scope}/{unique}/{filename}"

    def generate_private_url(self, key):
        return f"https://{self.config.bucket}.blob.core.windows.net/mindlogger/{key}"  # noqa

    def configure_client(self, _, **kwargs):
        blob_service_client = BlobServiceClient.from_connection_string(self.sec_key)
        with suppress(Exception):
            blob_service_client.create_container(self.default_container_name)

        return blob_service_client

    def _upload(self, path, body: BinaryIO):
        blob_client = self.client.get_blob_client(blob=path)
        blob_client.upload_blob(body)

    def _check_existence(self, bucket: str, key: str):
        blob_client = self.client.get_blob_client(self.default_container_name, blob=key)
        return blob_client.exists()

    def _generate_presigned_url(self, key: str):
        blob_client = self.client.get_blob_client(self.default_container_name, key)
        permissions = BlobSasPermissions(read=True)
        expiration = datetime.utcnow() + timedelta(seconds=self.config.ttl_signed_urls)
        sas_token = generate_blob_sas(
            account_name=self.client.account_name,
            container_name=self.default_container_name,
            blob_name=key,
            account_key=self.client.credential.account_key,
            permission=permissions,
            expiry=expiration,
        )
        presigned_url = blob_client.url + "?" + sas_token
        return presigned_url
