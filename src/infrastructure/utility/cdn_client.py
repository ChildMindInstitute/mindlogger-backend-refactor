import boto3
import io
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
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
            )
            self.bucket = config.bucket
        except KeyError:
            print("CDN configuration is not full")

    def upload(self, path, body: io.BytesIO):

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
    def generate_key(unique, filename, ext):
        return f"mindlogger/{unique}/{filename}.{ext}"

    def download(self, key):
        file = io.BytesIO()

        if self.env == "testing":
            local_file = open(key, "rb")
            file.write(local_file.read())
        else:
            self.client.download_fileobj(self.bucket, key, file)
        file.seek(0)
        return file
