import datetime

from pydantic import Field

from apps.applets.domain.base import AppletFetchBase
from apps.migrate.domain.activity_full import ActivityMigratedFull
from apps.migrate.domain.flow_full import FlowMigratedFull
from apps.shared.domain import InternalModel


class AppletMigratedFull(AppletFetchBase, InternalModel):
    migrated_date: datetime.datetime
    migrated_updated: datetime.datetime
    extra_fields: dict = Field(default_factory=dict)
    activities: list[ActivityMigratedFull] = Field(default_factory=list)
    activity_flows: list[FlowMigratedFull] = Field(default_factory=list)


class AppletMigratedHistoryFull(AppletFetchBase, InternalModel):
    migrated_date: datetime.datetime
    migrated_updated: datetime.datetime
    extra_fields: dict = Field(default_factory=dict)
    activities: list[ActivityMigratedFull] = Field(default_factory=list)
    activity_flows: list[FlowMigratedFull] = Field(default_factory=list)
