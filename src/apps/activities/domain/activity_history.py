import datetime
import uuid

from pydantic import Field, validator

from apps.activities.domain.activity_full import (
    PublicActivityFull,
    PublicActivityItemFull,
)
from apps.activities.domain.activity_item_history import ActivityItemHistory
from apps.activities.domain.scores_reports import (
    ScoresAndReports,
    SubscaleSetting,
)
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.domain.custom_validations import extract_history_version

__all__ = [
    "ActivityHistory",
    "ActivityHistoryChange",
    "PublicActivityHistoryChange",
    "ActivityHistoryExport",
    "ActivityHistoryFull",
]


class ActivityHistory(InternalModel):
    id: uuid.UUID
    applet_id: str
    id_version: str
    name: str
    description: dict
    splash_screen: str
    image: str
    show_all_at_once: bool
    is_skippable: bool
    is_reviewable: bool
    response_is_editable: bool
    order: int
    created_at: datetime.datetime
    scores_and_reports: ScoresAndReports | None = None
    subscale_setting: SubscaleSetting | None = None


class ActivityHistoryChange(InternalModel):
    name: str | None = None
    description: str | None = None
    splash_screen: str | None = None
    image: str | None = None
    show_all_at_once: str | None = None
    is_skippable: str | None = None
    is_reviewable: str | None = None
    response_is_editable: str | None = None
    order: str | None = None


class PublicActivityHistoryChange(PublicModel):
    name: str | None = None
    description: dict | None = None
    splash_screen: str | None = None
    image: str | None = None
    show_all_at_once: str | None = None
    is_skippable: str | None = None
    is_reviewable: str | None = None
    response_is_editable: str | None = None
    order: str | None = None


class ActivityHistoryFull(ActivityHistory):
    items: list[ActivityItemHistory] = Field(default_factory=list)


class ActivityHistoryExport(PublicActivityFull):
    id_version: str
    version: str | None = None
    items: list[PublicActivityItemFull] = Field(default_factory=list)

    _version = validator("version", always=True, allow_reuse=True)(
        extract_history_version
    )
