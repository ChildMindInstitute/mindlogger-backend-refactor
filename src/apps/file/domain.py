from pydantic import HttpUrl

from apps.shared.domain import PublicModel


class ContentUploadedFile(PublicModel):
    key: str
    url: str | None


class AnswerUploadedFile(ContentUploadedFile):
    file_id: str | None


class FileDownloadRequest(PublicModel):
    key: str


class FileCheckRequest(PublicModel):
    files: list[str]


class FileExistenceResponse(PublicModel):
    key: str
    uploaded: bool
    url: str | None = None
    file_id: str | None = None


class FilePresignRequest(PublicModel):
    private_urls: list[str | None]


class LogFileExistenceResponse(FileExistenceResponse):
    file_size: int | None  # file size in bytes


class FileNameRequest(PublicModel):
    file_name: str


class FileIdRequest(PublicModel):
    file_id: str


class PresignedUrl(PublicModel):
    upload_url: HttpUrl
    url: str
    # Use dict because fields can be different depend storage (AWS S3, Minio, GCS)
    fields: dict[str, str]
