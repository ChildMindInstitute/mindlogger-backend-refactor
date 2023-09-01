from apps.shared.domain import PublicModel


class UploadedFile(PublicModel):
    key: str
    url: str | None


class FileDownloadRequest(PublicModel):
    key: str


class FileCheckRequest(PublicModel):
    files: list[str]


class FileExistenceResponse(PublicModel):
    key: str
    uploaded: bool
    url: str | None = None


class FilePresignRequest(PublicModel):
    private_urls: list[str]
