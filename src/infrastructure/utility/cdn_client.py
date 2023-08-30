import io
import mimetypes
import uuid
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from apps.shared.exception import NotFoundError
from config.cdn import CDNSettings


class CDNClient:
    def __init__(self, config: CDNSettings, env: str):
        self.config = config
        self.env = env
        self.ttl_signed_urls = config.ttl_signed_urls
        self.client = self.configure_client(config)

    def configure_client(self, config):
        assert config, "set CDN"

        if self.env == "dev":
            return boto3.client(
                "s3",
                region_name=config.region,
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
            )
        try:
            return boto3.client("s3", region_name=config.region)
        except KeyError:
            print("CDN configuration is not full")

    def upload(self, path, body: BinaryIO):

        if self.env == "testing":
            # filename = path.split("/")[-1]
            # with open(filename, "wb") as file:
            #     file.write(body.getvalue())
            return
        self.client.upload_fileobj(
            body,
            Key=path,
            Bucket=self.config.bucket,
        )

    @staticmethod
    def generate_key(scope, unique, filename):
        return f"mindlogger/{scope}/{unique}/{uuid.uuid4()}/{filename}"

    def check_existence(self, key: str):
        try:
            return self.client.head_object(Bucket=self.config.bucket, Key=key)
        except ClientError:
            raise NotFoundError

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

    def generate_presigned_url(self, private_url):
        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.config.bucket,
                "Key": private_url,
            },
            ExpiresIn=self.ttl_signed_urls,
        )
        return url
