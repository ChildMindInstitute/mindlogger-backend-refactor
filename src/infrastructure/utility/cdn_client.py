import asyncio
import io
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from apps.shared.exception import NotFoundError
from infrastructure.utility.cdn_config import CdnConfig


class CDNClient:
    default_container_name = "mindlogger"

    def __init__(self, config: CdnConfig, env: str):
        self.config = config
        self.env = env
        self.client = self.configure_client(config)

    def generate_key(self, scope, unique, filename):
        return f"{self.default_container_name}/{scope}/{unique}/{filename}"

    def generate_private_url(self, key):
        return f"s3://{self.config.bucket}/{key}"

    def configure_client(self, config):
        assert config, "set CDN"

        if config.access_key and config.secret_key:
            return boto3.client(
                "s3",
                endpoint_url=config.endpoint_url,
                region_name=config.region,
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
            )
        try:
            return boto3.client("s3", region_name=config.region)
        except KeyError:
            print("CDN configuration is not full")

    def _upload(self, path, body: BinaryIO):
        if self.env == "testing":
            return
        self.client.upload_fileobj(
            body,
            Key=path,
            Bucket=self.config.bucket,
        )

    async def upload(self, path, body: BinaryIO):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._upload, path, body)
        await asyncio.wrap_future(future)

    def _check_existence(self, key: str):
        try:
            return self.client.head_object(Bucket=self.config.bucket, Key=key)
        except ClientError:
            raise NotFoundError

    async def check_existence(self, key: str):
        if self.env == "testing":
            return
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._check_existence, key)
            return await asyncio.wrap_future(future)

    def download(self, key):
        file = io.BytesIO()

        if self.env == "testing":
            local_file = open(key, "rb")
            file.write(local_file.read())
        else:
            self.client.download_fileobj(self.config.bucket, key, file)
        file.seek(0)
        media_type = (
            mimetypes.guess_type(key)[0]
            if mimetypes.guess_type(key)[0]
            else "application/octet-stream"
        )
        return file, media_type

    def _generate_presigned_url(self, key):
        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.config.bucket,
                "Key": key,
            },
            ExpiresIn=self.config.ttl_signed_urls,
        )
        return url

    async def generate_presigned_url(self, key):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._generate_presigned_url, key)
            url = await asyncio.wrap_future(future)
            return url

    async def delete_object(self, key: str | None):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                self.client.delete_object, Bucket=self.config.bucket, Key=key
            )
            await asyncio.wrap_future(future)

    async def list_object(self, key: str):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                self.client.list_objects, Bucket=self.config.bucket, Prefix=key
            )
            result = await asyncio.wrap_future(future)
            return result.get("Contents", [])
