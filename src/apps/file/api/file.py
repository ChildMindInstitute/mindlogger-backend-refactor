from fastapi import Body, UploadFile, File

from apps.file.domain import (
    DownloadFile,
    FileDownloadRequest,
    FileUploadRequest,
    UploadedFile,
)
from apps.shared.domain.response import Response


async def upload(
    file: FileUploadRequest = Body(...),
) -> Response[UploadedFile]:
    # TODO: generate key
    # TODO: upload file
    key: UploadedFile = "key"
    return Response(result=key)


async def download(
    key: FileDownloadRequest = Body(...),
) -> Response[DownloadFile]:
    # TODO: download file by given key
    # TODO: respond with the file
    file = File()
    return Response(result=file)
