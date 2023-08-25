from apps.shared.domain import PublicModel


class UploadedFile(PublicModel):
    key: str
    url: str


class FileDownloadRequest(PublicModel):
    key: str


class FileCheckRequest(PublicModel):
    files: list[str]


class FileExistenceResponse(PublicModel):
    key: str
    uploaded: bool
    url: str | None = None
