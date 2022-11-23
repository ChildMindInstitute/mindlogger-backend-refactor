import io
import uuid
from config.cdn import CDNSettings


class CDNClient:
    class ContentType:
        CSV = "application/csv"
        EXCEL = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        PDF = "application/pdf"

    def __init__(self, config: CDNSettings):
        self.client = None
        self.bucket = None
        self.endpoint = None
        self.env = "development"

        try:
            import boto3

            assert config, "set CDN"

            self.client = boto3.client(
                "s3",
                region_name=config.region,
                aws_access_key_id=config.access_key,
                aws_secret_access_key=config.secret_key,
            )
            self.bucket = config.bucket
            self.env = config.env
        except KeyError:
            print("CDN configuration is not full")
        except ImportError:
            print("Install boto3 in order to work with upload/download files.")

    def upload(self, path, body: io.BytesIO, content_type):
        assert self.client, "initialize client"
        if self.env == "testing":
            # filename = path.split("/")[-1]
            # with open(filename, "wb") as file:
            #     file.write(body.getvalue())
            return
        self.client.upload_fileobj(
            body,
            Key=path,
            Bucket=self.bucket,
            ExtraArgs={"ContentType": content_type},
        )

    @staticmethod
    def generate_key(unique, filename, ext):
        return f"mindlogger/{unique}/{filename}.{ext}"

    def download(self, key):
        file = io.BytesIO()
        assert self.client, "initialize client"
        if self.env == "testing":
            local_file = open(key, "rb")
            file.write(local_file.read())
        else:
            self.client.download_fileobj(self.bucket, key, file)
        file.seek(0)
        return file
