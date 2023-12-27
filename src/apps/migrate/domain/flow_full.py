from pydantic import Field

from apps.activity_flows.domain.flow_full import FlowFull


class FlowMigratedFull(FlowFull):
    extra_fields: dict = Field(default_factory=dict)
