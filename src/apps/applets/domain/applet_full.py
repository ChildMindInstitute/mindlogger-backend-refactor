from typing import Annotated

from pydantic import Field

from apps.activities.domain import ActivityHistoryFull
from apps.activities.domain.activity_full import ActivityFull, PublicActivityFull
from apps.activity_flows.domain.flow_full import FlowFull, FlowHistoryFull, PublicFlowFull
from apps.applets.domain.base import AppletFetchBase
from apps.shared.domain import InternalModel, PublicModel


class AppletFull(AppletFetchBase, InternalModel):
    activities: Annotated[list[ActivityFull], Field(default_factory=list)]
    activity_flows: Annotated[list[FlowFull], Field(default_factory=list)]


class PublicAppletFull(AppletFetchBase, PublicModel):
    activities: Annotated[list[PublicActivityFull], Field(default_factory=list)]
    activity_flows: Annotated[list[PublicFlowFull], Field(default_factory=list)]


class AppletHistoryFull(AppletFetchBase, InternalModel):
    activities: Annotated[list[ActivityHistoryFull], Field(default_factory=list)]
    activity_flows: Annotated[list[FlowHistoryFull], Field(default_factory=list)]
