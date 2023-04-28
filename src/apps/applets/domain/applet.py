import datetime
import uuid

from pydantic import Field, PositiveInt

from apps.activities.domain.activity import (
    ActivitySingleLanguageDetail,
    ActivitySingleLanguageDetailPublic,
)
from apps.activity_flows.domain.flow import (
    FlowSingleLanguageDetail,
    FlowSingleLanguageDetailPublic,
)
from apps.applets.domain.base import AppletBaseInfo, AppletFetchBase
from apps.shared.domain import InternalModel, PublicModel
from apps.themes.domain import PublicTheme, Theme
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
    theme: PublicTheme | None = None


class AppletSingleLanguageInfo(AppletFetchBase, InternalModel):
    description: str  # type: ignore[assignment]
    about: str  # type: ignore[assignment]
    theme: Theme | None


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
    period: PositiveInt
    retention: DataRetention
