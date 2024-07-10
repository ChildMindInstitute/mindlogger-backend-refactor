import enum

from pydantic import AnyHttpUrl

from apps.shared.domain import PublicModel


class WebmTargetExtenstion(str, enum.Enum):
    MP3 = ".mp3"
    MP4 = ".mp4"


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
    uploaded: bool
    url: str | None = None
    file_id: str | None = None


class FilePresignRequest(PublicModel):
    private_urls: list[str | None]


class LogFileExistenceResponse(FileExistenceResponse):
    file_size: int | None  # file size in bytes
    key: str


class FileNameRequest(PublicModel):
    file_name: str
    target_extension: WebmTargetExtenstion | None = None


class FileIdRequest(PublicModel):
    file_id: str


class PresignedUrl(PublicModel):
    upload_url: AnyHttpUrl
    url: str
    # Use dict because fields can be different depend storage (AWS S3, Minio, GCS)
    fields: dict[str, str]
