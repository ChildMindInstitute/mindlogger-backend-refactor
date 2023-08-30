from typing import BinaryIO, Optional

import boto3
from azure.storage.blob import BlobServiceClient

from config.cdn import CDNSettings
from infrastructure.utility.cdn_client import CDNClient


class CdnClientS3(CDNClient):
    def __init__(
        self,
        region: str,
        acc_key: str,
        sec_key: str,
        domain: Optional[str] = None,
        bucket: Optional[str] = None,
        env: str = "",
    ):
        self.acc_key = acc_key
        self.sec_key = sec_key
        self.region = region
        self.config = CDNSettings(
            region=region, bucket=bucket, domain=domain if domain else ""
        )
        super().__init__(self.config, env)

    def configure_client(self, config):
        return boto3.client(
            "s3",
            aws_access_key_id=self.acc_key,
            aws_secret_access_key=self.sec_key,
            region_name=self.region,
        )


class CdnClientBlob(CDNClient):
    def __init__(self, sec_key: str, env: str = ""):
        self.sec_key = sec_key
        config = CDNSettings(region="", bucket="", domain="")
        super().__init__(config, env)

    def configure_client(self, _):
        return BlobServiceClient.from_connection_string(self.sec_key)

    def upload(self, path, body: BinaryIO):
        blob_client = self.client.get_blob_client(blob=path)
        blob_client.upload_blob(body)
