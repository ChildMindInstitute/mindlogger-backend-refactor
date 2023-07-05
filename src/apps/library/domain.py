import uuid

from pydantic import validator

from apps.shared.domain import InternalModel, PublicModel, validate_uuid


class AppletLibrary(InternalModel):
    applet_id_version: str
    keywords: list[str] | None = None


class AppletLibraryFull(AppletLibrary):
    id: uuid.UUID


class AppletLibraryInfo(PublicModel):
    library_id: uuid.UUID
    url: str


class AppletLibraryCreate(InternalModel):
    applet_id: uuid.UUID
    keywords: list[str] | None = None
    name: str


class AppletLibraryUpdate(InternalModel):
    keywords: list[str] | None = None
    name: str


class LibraryNameCheck(InternalModel):
    name: str


class LibraryItemActivityItem(InternalModel):
    id: uuid.UUID
    question: dict[str, str] | None = None
    response_type: str
    response_values: list | dict | None = None
    order: int
    name: str


class LibraryItemActivity(InternalModel):
    id: uuid.UUID
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
    activities: list[LibraryItemActivity]


class LibraryQueryParams(InternalModel):
    search: str | None = None


class CartItemActivity(InternalModel):
    activity_id: str
    items: list[str] | None = None

    @validator("activity_id")
    def validate_id(cls, value):
        return validate_uuid(value)


class CartItem(PublicModel):
    library_id: str
    activities: list[CartItemActivity]

    @validator("library_id")
    def validate_id(cls, value):
        return validate_uuid(value)


class Cart(PublicModel):
    cart_items: list[CartItem] | None = None
