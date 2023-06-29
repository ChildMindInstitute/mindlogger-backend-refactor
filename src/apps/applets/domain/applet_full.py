from pydantic import Field

from apps.activities.domain import ActivityHistoryFull
from apps.activities.domain.activity_full import (
    ActivityFull,
    PublicActivityFull,
)
from apps.activity_flows.domain.flow_full import (
    FlowFull,
    FlowHistoryFull,
    PublicFlowFull,
)
from apps.applets.domain.base import AppletFetchBase
from apps.shared.domain import InternalModel, PublicModel


class AppletFull(AppletFetchBase, InternalModel):
    activities: list[ActivityFull] = Field(default_factory=list)
    activity_flows: list[FlowFull] = Field(default_factory=list)


class PublicAppletFull(AppletFetchBase, PublicModel):
    activities: list[PublicActivityFull] = Field(default_factory=list)
    activity_flows: list[PublicFlowFull] = Field(default_factory=list)


class AppletHistoryFull(AppletFetchBase, InternalModel):
    activities: list[ActivityHistoryFull] = Field(default_factory=list)
    activity_flows: list[FlowHistoryFull] = Field(default_factory=list)
