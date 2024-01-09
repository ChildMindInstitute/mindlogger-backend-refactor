import datetime
import uuid

from pydantic import Field, PositiveInt, root_validator

from apps.activities.domain.activity import (
    ActivityLanguageWithItemsMobileDetailPublic,
    ActivitySingleLanguageDetail,
    ActivitySingleLanguageDetailPublic,
    ActivitySingleLanguageMobileDetailPublic,
)
from apps.activities.errors import PeriodIsRequiredError
from apps.activity_flows.domain.flow import (
    FlowSingleLanguageDetail,
    FlowSingleLanguageDetailPublic,
    FlowSingleLanguageMobileDetailPublic,
)
from apps.applets.domain.base import (
    AppletBaseInfo,
    AppletFetchBase,
    Encryption,
)
from apps.shared.domain import InternalModel, PublicModel, Response
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

    activities: list[ActivitySingleLanguageDetail] = Field(
        default_factory=list
    )
    activity_flows: list[FlowSingleLanguageDetail] = Field(
        default_factory=list
    )
    theme: Theme | None = None


class AppletSingleLanguageDetailPublic(AppletFetchBase, PublicModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivitySingleLanguageDetailPublic] = Field(
        default_factory=list
    )
    activity_flows: list[FlowSingleLanguageDetailPublic] = Field(
        default_factory=list
    )
    theme: PublicTheme | None = None


class AppletSingleLanguageDetailMobilePublic(PublicModel):
    id: uuid.UUID
    display_name: str
    version: str
    description: str
    about: str
    image: str = ""
    watermark: str = ""
    theme: PublicThemeMobile | None = None
    activities: list[ActivitySingleLanguageMobileDetailPublic] = Field(
        default_factory=list
    )
    activity_flows: list[FlowSingleLanguageMobileDetailPublic] = Field(
        default_factory=list
    )
    encryption: Encryption | None
    stream_enabled: bool | None
    stream_ip_address: str | None
    stream_port: int | None


class AppletSingleLanguageDetailForPublic(AppletBaseInfo, PublicModel):
    id: uuid.UUID
    version: str
    created_at: datetime.datetime | None
    updated_at: datetime.datetime | None
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivitySingleLanguageDetailPublic] = Field(
        default_factory=list
    )
    activity_flows: list[FlowSingleLanguageDetailPublic] = Field(
        default_factory=list
    )
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


class AppletRetrieveResponse(Response[AppletSingleLanguageDetailPublic]):
    respondent_meta: dict | None = None


class AppletActivitiesDetailsPublic(PublicModel):
    activities_details: list[
        ActivityLanguageWithItemsMobileDetailPublic
    ] = Field(default_factory=list)
    applet_detail: AppletSingleLanguageDetailMobilePublic
    respondent_meta: dict | None = None
