import io
import mimetypes
import uuid
from typing import BinaryIO

import boto3

from config.cdn import CDNSettings


class CDNClient:
    def __init__(self, config: CDNSettings, env: str):
        self.bucket = None
        self.endpoint = None
        self.env = env

        try:

            assert config, "set CDN"

            self.client = boto3.client(
                "s3",
                region_name=config.region,
            )
            self.bucket = config.bucket
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
            Bucket=self.bucket,
        )

    @staticmethod
    def generate_key(unique, filename):
        return f"mindlogger/{unique}/{uuid.uuid4()}/{filename}"

    def download(self, key):
        file = io.BytesIO()

        if self.env == "testing":
            local_file = open(key, "rb")
            file.write(local_file.read())
        else:
            self.client.download_fileobj(self.bucket, key, file)
        file.seek(0)
        media_type = (
            mimetypes.guess_type(key)[0]
            if mimetypes.guess_type(key)[0]
            else "application/octet-stream"
        )
        return file, media_type
