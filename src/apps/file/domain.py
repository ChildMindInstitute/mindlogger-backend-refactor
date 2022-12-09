from pydantic import FilePath

from apps.shared.domain import PublicModel


class FileUploadRequest(PublicModel):
    file: FilePath


class UploadedFile(PublicModel):
    key: str


class FileDownloadRequest(PublicModel):
    key: str


class DownloadFile(PublicModel):
    file: FilePath
