import uuid

from pydantic import Field, validator

from apps.shared.domain import (
    InternalModel,
    PublicModel,
    dict_keys_to_camel_case,
    to_camelcase,
)


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
    question: dict[str, str] | None = None
    response_type: str
    response_values: list | dict | None = None
    config: dict | None = None
    name: str
    is_hidden: bool | None = False
    conditional_logic: dict | None = None
    allow_edit: bool | None = None

    @validator("config", pre=True)
    def convert_config_keys(cls, config):
        if config is not None:
            return dict_keys_to_camel_case(config)
        return config

    @validator("response_values", pre=True)
    def convert_response_values_keys(cls, response_values):
        if response_values:
            if isinstance(response_values, dict):
                return dict_keys_to_camel_case(response_values)
            elif isinstance(response_values, list):
                return [to_camelcase(value) for value in response_values]
        return response_values


class LibraryItemActivity(InternalModel):
    key: uuid.UUID
    name: str
    description: dict[str, str]
    image: str
    splash_screen: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
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


class _LibraryItem(InternalModel):
    id: uuid.UUID
    display_name: str
    description: dict[str, str] | None = None
    about: dict[str, str] | None = None
    image: str = ""
    watermark: str = ""
    theme_id: uuid.UUID | None = None
    keywords: list[str] | None = None
    activities: list[LibraryItemActivity] | None = None
    activity_flows: list[LibraryItemFlow] | None = None


class LibraryItem(_LibraryItem):
    applet_id_version: str


class PublicLibraryItem(_LibraryItem):
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
