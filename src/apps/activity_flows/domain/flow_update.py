import uuid
from gettext import gettext as _
from typing import Self

from pydantic import model_validator

from apps.activity_flows.domain.base import FlowBase
from apps.shared.domain import PublicModel


class ActivityFlowItemUpdate(PublicModel):
    id: uuid.UUID | None = None
    activity_key: uuid.UUID


class PreparedFlowItemUpdate(PublicModel):
    id: uuid.UUID | None = None
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID


class FlowUpdate(FlowBase, PublicModel):
    id: uuid.UUID | None = None
    items: list[ActivityFlowItemUpdate]


class ActivityFlowReportConfiguration(PublicModel):
    report_included_activity_name: str | None = None
    report_included_item_name: str | None = None

    @model_validator(mode="after")
    def validate_score_required(self) -> Self:
        activity_name = self.report_included_activity_name
        item_name = self.report_included_item_name
        if activity_name and not item_name:
            raise ValueError(_('Flow "activityName" missed'))
        if not activity_name and item_name:
            raise ValueError(_('Flow "itemName" missed'))
        return self
