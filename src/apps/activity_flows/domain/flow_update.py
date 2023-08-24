import uuid
from gettext import gettext as _

from pydantic import root_validator

from apps.activity_flows.domain.base import FlowBase
from apps.shared.domain import InternalModel, PublicModel


class ActivityFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_key: uuid.UUID


class PreparedFlowItemUpdate(InternalModel):
    id: uuid.UUID | None
    activity_flow_id: uuid.UUID
    activity_id: uuid.UUID


class FlowUpdate(FlowBase, InternalModel):
    id: uuid.UUID | None
    items: list[ActivityFlowItemUpdate]


class ActivityFlowReportConfiguration(PublicModel):
    report_included_activity_name: str | None
    report_included_item_name: str | None

    @root_validator()
    def validate_score_required(cls, values):
        activity_name = values.get("report_included_activity_name")
        item_name = values.get("report_included_item_name")
        if activity_name and not item_name:
            raise ValueError(_('Flow "activityName" missed'))
        if not activity_name and item_name:
            raise ValueError(_('Flow "itemName" missed'))
        return values
