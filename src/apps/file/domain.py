from apps.shared.domain import PublicModel


class UploadedFile(PublicModel):
    key: str


class FileDownloadRequest(PublicModel):
    key: str
