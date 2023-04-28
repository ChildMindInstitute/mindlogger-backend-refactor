from apps.shared.domain import PublicModel


class UploadedFile(PublicModel):
    key: str
    url: str


class FileDownloadRequest(PublicModel):
    key: str
