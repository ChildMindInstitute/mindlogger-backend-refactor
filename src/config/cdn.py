from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    secret_key: str = "0Bdiw4ajymm9FD4752b6PEL962CsjPpMTru06oFy"
    access_key: str = "AKIAVGNWTLO55ZUXJN5I"
    region: str = "us-east-1"
    bucket: str = "tom12-test-bucket"

    @property
    def url(self):
        return f"https://{self.bucket}.s3.amazonaws.com/{{key}}"
