import asyncio
import io
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from apps.file.errors import FileNotFoundError
from apps.shared.exception import NotFoundError
from infrastructure.logger import logger
from infrastructure.utility.cdn_config import CdnConfig


class ObjectNotFoundError(Exception):
    pass


class CDNClient:
    default_container_name = "mindlogger"

    def __init__(self, config: CdnConfig, env: str):
        self.config = config
        self.env = env
        self.client = self.configure_client(config)

    @classmethod
    def generate_key(cls, scope, unique, filename):
        return f"{cls.default_container_name}/{scope}/{unique}/{filename}"

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
        # TODO: do we need this? If exception is caught self.client will be None
        except KeyError:
            logger.warning("CDN configuration is not full")

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

    def _check_existence(self, bucket: str, key: str):
        try:
            return self.client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            logger.warning(f"Error when trying to check existence for {key} in {bucket}: {e}")
            raise NotFoundError

    async def check_existence(self, bucket: str, key: str):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._check_existence, bucket, key)
            return await asyncio.wrap_future(future)

    def download(self, key, file: BinaryIO | None = None):
        if not file:
            file = io.BytesIO()

        try:
            self.client.download_fileobj(self.config.bucket, key, file)
        except ClientError as e:
            if int(e.response.get("Error", {}).get("Code", "0")) == 404:
                logger.warning(f"Trying to download not existing file {key}")
                raise ObjectNotFoundError()
            logger.error(f"Error when trying to download file {key}: {e}")
            raise
        except EndpointConnectionError as e:
            logger.error(f"Error when trying to download file {key}: {e}")
            raise FileNotFoundError

        file.seek(0)
        media_type = mimetypes.guess_type(key)[0] if mimetypes.guess_type(key)[0] else "application/octet-stream"
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
            future = executor.submit(self.client.delete_object, Bucket=self.config.bucket, Key=key)
            await asyncio.wrap_future(future)

    async def list_object(self, key: str):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self.client.list_objects, Bucket=self.config.bucket, Prefix=key)
            result = await asyncio.wrap_future(future)
            return result.get("Contents", [])

    def generate_presigned_post(self, bucket, key):
        # Not needed ThreadPoolExecutor because there is no any IO operation (no API calls to s3)
        return self.client.generate_presigned_post(bucket, key, ExpiresIn=self.config.ttl_signed_urls)
