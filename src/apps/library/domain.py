import uuid

from apps.shared.domain import InternalModel


class AppletLibrary(InternalModel):
    applet_id_version: str
    keywords: list[str] | None = None


class AppletLibraryFull(AppletLibrary):
    id: uuid.UUID


class AppletLibraryCreate(InternalModel):
    applet_id: uuid.UUID
    keywords: list[str] | None = None
    name: str


class LibraryNameCheck(InternalModel):
    name: str
