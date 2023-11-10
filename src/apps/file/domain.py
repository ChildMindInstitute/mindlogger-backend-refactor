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
