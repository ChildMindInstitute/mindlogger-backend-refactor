import asyncio
import http
import io
import json
import mimetypes
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO

import boto3
import httpx
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from apps.file.errors import FileNotFoundError
from apps.shared.exception import NotFoundError
from infrastructure.logger import logger
from infrastructure.storage.cdn_config import CdnConfig


class ObjectNotFoundError(Exception):
    pass


class CDNClient:
    KEY_KEY = "Key"
    KEY_CHECKSUM = "ETag"

    default_container_name = "mindlogger"
    meta_last_modified = "last_modified_orig"

    def __init__(self, config: CdnConfig, env: str, *, max_concurrent_tasks: int = 10):
        self.config = config
        self.env = env
        self.client = self._configure_client(config)

        # semaphore for concurrent calls of urlib3 in boto3
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

        self._is_bucket_public: bool | None = None

    @classmethod
    def generate_key(cls, scope, unique, filename):
        return f"{cls.default_container_name}/{scope}/{unique}/{filename}"

    def generate_private_url(self, key):
        return f"s3://{self.config.bucket}/{key}"

    def _configure_client(self, config):
        assert config, "set CDN"
        client_config = Config(
            max_pool_connections=25,
        )

        if config.access_key and config.secret_key:
            return boto3.client(
                "s3",
                endpoint_url=config.endpoint_url,
                region_name=config.region,
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
                config=client_config,
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

    def _check_existence(self, key: str):
        try:
            return self.client.head_object(Bucket=self.config.bucket, Key=key)
        except ClientError as e:
            # TODO The actual error for not found is S3.Client.exceptions.NoSuchKey
            logger.warning(f"Error when trying to check existence for {key} in {self.config.bucket}: {e}")
            raise NotFoundError

    async def check_existence(self, key: str):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._check_existence, key)
            return await asyncio.wrap_future(future)

    def download(self, key, file: BinaryIO | None = None):
        """
        Download a file from a CDN location to a local directory.  It is up to the caller to
        clean up the file after use.
        """
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
        async with self.semaphore:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self.client.delete_object, Bucket=self.config.bucket, Key=key)
                await asyncio.wrap_future(future)

    async def list_object(self, key: str):
        async with self.semaphore:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self.client.list_objects, Bucket=self.config.bucket, Prefix=key)
                result = await asyncio.wrap_future(future)
                return result.get("Contents", [])

    def generate_presigned_post(self, key):
        # Not needed ThreadPoolExecutor because there is no any IO operation (no API calls to s3)
        return self.client.generate_presigned_post(self.config.bucket, key, ExpiresIn=self.config.ttl_signed_urls)

    def _copy(self, key, storage_from: "CDNClient", key_from: str | None = None) -> int:
        key_from = key_from or key
        res = storage_from.client.get_object(Bucket=storage_from.config.bucket, Key=key_from)
        file_obj = res["Body"]
        metadata: dict = res["Metadata"]
        last_modified = res["LastModified"]

        metadata.setdefault(self.meta_last_modified, last_modified.strftime("%Y-%m-%dT%H:%M:%S"))

        self.client.upload_fileobj(
            file_obj,
            self.config.bucket,
            key,
            ExtraArgs={
                "Metadata": metadata,
            },
        )

        return res["ContentLength"]

    async def copy(self, key, storage_from: "CDNClient", key_from: str | None = None) -> int:
        async with self.semaphore:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self._copy, key, storage_from, key_from=key_from)
                res = await asyncio.wrap_future(future)
                return res

    async def check(self):
        storage_bucket = self.config.bucket
        logger.info(f'Check bucket "{storage_bucket}" availability.')
        key = "mindlogger.txt"

        presigned_data = self.generate_presigned_post(storage_bucket, key)

        logger.info(f"Presigned POST fields are following: {presigned_data['fields'].keys()}")
        file = io.BytesIO(b"")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    presigned_data["url"], data=presigned_data["fields"], files={"file": (key, file)}
                )
                if response.status_code == http.HTTPStatus.NO_CONTENT:
                    logger.info(f"Bucket {storage_bucket} is available.")
                else:
                    logger.info(response.content)
                    raise Exception("File upload error")
            except httpx.HTTPError as e:
                logger.info("File upload error")
                raise e

    def _check_is_bucket_public(self) -> bool:
        # Check the bucket policy
        try:
            bucket_policy = self.client.get_bucket_policy(Bucket=self.config.bucket)
            if policy := bucket_policy.get("Policy"):
                policy_statements: list = json.loads(policy)["Statement"]

                for statement in policy_statements:
                    if statement["Effect"] == "Allow" and "Principal" in statement and statement["Principal"] == "*":
                        return True  # Bucket policy allows public access
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucketPolicy":
                logger.error(f"Error getting bucket policy: {e}")
        except Exception as e:
            logger.error(f"Error getting bucket policy: {e}")

        return False  # No public access found

    def is_bucket_public(self) -> bool:
        if self._is_bucket_public is None:
            self._is_bucket_public = self._check_is_bucket_public()

        return self._is_bucket_public

    def _is_object_public(self, key) -> bool:
        # Check the object's ACL
        try:
            acl = self.client.get_object_acl(Bucket=self.config.bucket, Key=key)
            for grant in acl["Grants"]:
                if (
                    grant["Grantee"].get("Type") == "Group"
                    and grant["Grantee"].get("URI") == "http://acs.amazonaws.com/groups/global/AllUsers"
                ):
                    return True  # Object is publicly accessible
        except (ClientError, Exception) as e:
            logger.error(f"Error getting object ACL: {e}")
            return False

        return False  # No public access found

    async def is_object_public(self, key) -> bool:
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self._is_object_public, key)
            return await asyncio.wrap_future(future)
