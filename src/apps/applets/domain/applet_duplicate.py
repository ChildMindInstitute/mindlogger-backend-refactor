from pydantic import Field, PositiveInt

from apps.activities.domain.activity import ActivityDuplicate
from apps.activity_flows.domain.flow import FlowDuplicate
from apps.applets.domain.base import AppletFetchBase
from apps.themes.domain import Theme
from apps.workspaces.domain.constants import DataRetention


class AppletDuplicate(AppletFetchBase):
    retention_period: PositiveInt | None = None
    retention_type: DataRetention | None = None

    activities: list[ActivityDuplicate] = Field(default_factory=list)
    activity_flows: list[FlowDuplicate] = Field(default_factory=list)
    theme: Theme | None = None
    encryption: None
