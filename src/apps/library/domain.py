import uuid

from apps.shared.domain import InternalModel, PublicModel


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


class LibraryItemActivityItem(InternalModel):
    question: dict[str, str] | None = None
    response_type: str
    response_values: list | dict | None = None
    order: int
    name: str


class LibraryItemActivity(InternalModel):
    name: str
    items: list[LibraryItemActivityItem] | None = None


class LibraryItem(InternalModel):
    id: uuid.UUID
    applet_id_version: str
    display_name: str
    keywords: list[str] | None = None
    description: dict[str, str] | None = None
    activities: list[LibraryItemActivity] | None = None


class PublicLibraryItem(PublicModel):
    id: uuid.UUID
    version: str
    display_name: str
    keywords: list[str] | None = None
    description: dict[str, str] | None = None
    activities: list[LibraryItemActivity] | None = None


class LibraryQueryParams(InternalModel):
    search: str | None = None
