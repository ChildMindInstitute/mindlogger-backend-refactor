import datetime
import uuid
from typing import Generic

from pydantic import Field, IPvAnyAddress, PositiveInt, root_validator
from pydantic.generics import GenericModel

from apps.activities.domain.activity import (
    ActivityBaseInfo,
    ActivityLanguageWithItemsMobileDetailPublic,
    ActivitySingleLanguageDetail,
    ActivitySingleLanguageDetailPublic,
    ActivitySingleLanguageMobileDetailPublic,
)
from apps.activities.errors import PeriodIsRequiredError
from apps.activity_flows.domain.flow import (
    FlowBaseInfo,
    FlowSingleLanguageDetail,
    FlowSingleLanguageDetailPublic,
    FlowSingleLanguageMobileDetailPublic,
)
from apps.applets.domain.base import AppletBaseInfo, AppletFetchBase, Encryption
from apps.shared.domain import InternalModel, PublicModel, _BaseModel
from apps.themes.domain import PublicTheme, PublicThemeMobile, Theme
from apps.workspaces.domain.constants import DataRetention


class Applet(AppletFetchBase, InternalModel):
    pass


class AppletPublic(AppletFetchBase, PublicModel):
    pass


class AppletSingleLanguageDetail(AppletFetchBase, InternalModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivitySingleLanguageDetail] = Field(default_factory=list)
    activity_flows: list[FlowSingleLanguageDetail] = Field(default_factory=list)
    theme: Theme | None = None


class AppletSingleLanguageDetailPublic(AppletFetchBase, PublicModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivitySingleLanguageDetailPublic] = Field(default_factory=list)
    activity_flows: list[FlowSingleLanguageDetailPublic] = Field(default_factory=list)
    theme: PublicTheme | None = None


class AppletMinimumInfo(PublicModel):
    display_name: str
    version: str
    description: str
    about: str
    image: str = ""
    watermark: str = ""


class AppletSingleLanguageDetailMobilePublic(AppletMinimumInfo, PublicModel):
    id: uuid.UUID
    theme: PublicThemeMobile | None = None
    activities: list[ActivitySingleLanguageMobileDetailPublic] = Field(default_factory=list)
    activity_flows: list[FlowSingleLanguageMobileDetailPublic] = Field(default_factory=list)
    encryption: Encryption | None
    stream_enabled: bool | None
    stream_ip_address: IPvAnyAddress | None
    stream_port: PositiveInt | None
    integrations: list[str] | None


class AppletSingleLanguageDetailForPublic(AppletBaseInfo, PublicModel):
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivitySingleLanguageDetailPublic] = Field(default_factory=list)
    activity_flows: list[FlowSingleLanguageDetailPublic] = Field(default_factory=list)
    theme: PublicTheme
    encryption: Encryption | None


class AppletSingleLanguageInfo(AppletFetchBase, InternalModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    theme: Theme | None
    is_pinned: bool = False


class AppletSingleLanguageInfoPublic(AppletFetchBase, PublicModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    theme: PublicTheme | None


class AppletName(InternalModel):
    name: str
    exclude_applet_id: uuid.UUID | None


class AppletUniqueName(PublicModel):
    name: str


class AppletDataRetention(InternalModel):
    retention: DataRetention
    period: PositiveInt | None = None

    @root_validator()
    def validate_period(cls, values):
        retention = values.get("retention")
        value = values.get("period")
        if retention != DataRetention.INDEFINITELY and not value:
            raise PeriodIsRequiredError()
        if retention == DataRetention.INDEFINITELY:
            values["period"] = None
        return values


class AppletRetrieveResponse(PublicModel, GenericModel, Generic[_BaseModel]):
    result: _BaseModel
    respondent_meta: dict | None = None


class AppletActivitiesDetailsPublic(PublicModel):
    activities_details: list[ActivityLanguageWithItemsMobileDetailPublic] = Field(default_factory=list)
    applet_detail: AppletSingleLanguageDetailMobilePublic
    respondent_meta: dict | None = None


class AppletActivitiesBaseInfo(AppletMinimumInfo, PublicModel):
    id: uuid.UUID
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
    activities: list[ActivityBaseInfo]
    activity_flows: list[FlowBaseInfo]
