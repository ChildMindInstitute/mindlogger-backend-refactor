import io
import uuid


class CDNClient:
    class ContentType:
        CSV = "application/csv"
        EXCEL = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        PDF = "application/pdf"

    def __init__(self):
        self.client = None
        self.bucket = None
        self.endpoint = None
        self.env = "development"

    def create_client(self, config: dict):
        try:
            import boto3

            assert "SECRET_KEY" in config, "set SECRET_KEY"
            assert "ACCESS_KEY" in config, "set ACCESS_KEY"
            assert "REGION" in config, "set REGION"
            assert "BUCKET" in config, "set BUCKET"

            self.client = boto3.client(
                "s3",
                region_name=config["REGION"],
                aws_access_key_id=config["ACCESS_KEY"],
                aws_secret_access_key=config["SECRET_KEY"],
            )
            self.bucket = config["BUCKET"]
            self.env = config["ENV"]
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
