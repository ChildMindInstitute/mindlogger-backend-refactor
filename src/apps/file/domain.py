from apps.shared.domain import PublicModel


class UploadedFile(PublicModel):
    key: str
    url: str


class FileDownloadRequest(PublicModel):
    key: str


class FileCheckRequest(PublicModel):
    files: list[str]


class FileExistenceResponse(PublicModel):
    file_id: str
    uploaded: bool
    remote_url: str | None = None
