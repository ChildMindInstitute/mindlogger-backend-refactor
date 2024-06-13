import uuid

from pydantic import BaseModel, Field, validator

from apps.activities.domain.response_type_config import PerformanceTaskType
from apps.shared.domain import InternalModel, PublicModel


class AppletLibrary(InternalModel):
    applet_id_version: str
    keywords: list[str] = []


class AppletLibraryFull(AppletLibrary):
    id: uuid.UUID


class AppletLibraryInfo(PublicModel):
    library_id: uuid.UUID
    url: str


class AppletLibraryCreate(InternalModel):
    applet_id: uuid.UUID
    keywords: list[str] | None = []
    name: str

    @validator("keywords", pre=True)
    def set_keywords(cls, keywords: list[str] | None):
        return keywords if keywords is not None else []


class AppletLibraryUpdate(InternalModel):
    keywords: list[str] = []
    name: str


class LibraryNameCheck(InternalModel):
    name: str


class LibraryItemActivityItem(InternalModel):
    question: dict[str, str] | None = None
    response_type: str
    response_values: list | dict | None = None
    config: dict | None = None
    name: str
    is_hidden: bool | None = False
    conditional_logic: dict | None = None
    allow_edit: bool | None = None


class LibraryItemActivity(InternalModel):
    key: uuid.UUID
    name: str
    description: dict[str, str]
    image: str
    splash_screen: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    is_performance_task: bool = False
    performance_task_type: PerformanceTaskType | None = None
    response_is_editable: bool = False
    is_hidden: bool | None = False
    scores_and_reports: dict | None = None
    subscale_setting: dict | None = None
    items: list[LibraryItemActivityItem] | None = None


class LibraryItemFlowItem(InternalModel):
    activity_key: uuid.UUID


class LibraryItemFlow(InternalModel):
    name: str
    description: dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    is_hidden: bool | None = False
    items: list[LibraryItemFlowItem]


class _LibraryItem(BaseModel):
    id: uuid.UUID
    display_name: str
    description: dict[str, str] | None = None
    about: dict[str, str] | None = None
    image: str = ""
    theme_id: uuid.UUID | None = None
    keywords: list[str] = []
    activities: list[LibraryItemActivity] | None = None
    activity_flows: list[LibraryItemFlow] | None = None

    @validator("keywords", pre=True)
    def validate_keywords(cls, keywords: list[str] | None) -> list[str]:
        return keywords if keywords is not None else []


class LibraryItem(InternalModel, _LibraryItem):
    applet_id_version: str


class PublicLibraryItem(PublicModel, _LibraryItem):
    version: str


class LibraryQueryParams(InternalModel):
    search: str | None = None
    page: int = Field(gt=0, default=1)
    limit: int = Field(gt=0, default=10)


class Cart(PublicModel):
    cart_items: list[dict] | None = None


class CartItem(LibraryItem):
    pass


class CartQueryParams(LibraryQueryParams):
    pass
