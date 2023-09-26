import datetime
import uuid

from pydantic import Field, validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_full import (
    ActivityItemHistoryFull,
    PublicActivityFull,
    PublicActivityItemFull,
)
from apps.activities.domain.activity_item import (
    ActivityItemSingleLanguageDetailPublic,
)
from apps.activities.domain.activity_item_history import (
    ActivityItemHistoryChange,
)
from apps.activities.domain.response_type_config import PerformanceTaskType
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

from apps.shared.locale import I18N


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
    report_included_item_name: str | None = None
    order: int
    created_at: datetime.datetime
    is_hidden: bool | None = False
    scores_and_reports: ScoresAndReports | None = None
    subscale_setting: SubscaleSetting | None = None


class ActivityHistoryChange(InternalModel):
    name: str | None = None
    changes: list[str] | None = Field(default_factory=list)
    items: list[ActivityItemHistoryChange] | None = Field(default_factory=list)


class PublicActivityHistoryChange(PublicModel):
    name: str | None = None
    changes: list[str] | None = Field(default_factory=list)
    items: list[ActivityItemHistoryChange] | None = Field(default_factory=list)


class ActivityHistoryFull(ActivityHistory):
    items: list[ActivityItemHistoryFull] = Field(default_factory=list)


class ActivityHistoryExport(PublicActivityFull):
    id_version: str
    version: str | None = None
    items: list[PublicActivityItemFull] = Field(default_factory=list)

    _version = validator("version", always=True, allow_reuse=True)(
        extract_history_version
    )

    def translate(self, i18n: I18N) -> "ActivityHistoryTranslatedExport":
        as_dict = self.dict(by_alias=False)
        as_dict["description"] = i18n.translate(self.description)

        items = []
        for item in self.items:
            itms_dict = item.dict(by_alias=False)
            itms_dict["question"] = i18n.translate(item.question)
            items.append(ActivityItemSingleLanguageDetailPublic(**itms_dict))
        as_dict["items"] = items

        return ActivityHistoryTranslatedExport(**as_dict)


class ActivityHistoryTranslatedExport(ActivityBase, PublicModel):
    id: uuid.UUID
    id_version: str
    version: str | None = None
    description: str  # type: ignore[assignment]
    created_at: datetime.datetime
    is_performance_task: bool = False
    performance_task_type: PerformanceTaskType | None = None
    items: list[ActivityItemSingleLanguageDetailPublic] = Field(
        default_factory=list
    )
