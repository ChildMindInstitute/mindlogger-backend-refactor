from enum import Enum

from apps.shared.domain import InternalModel


class AvailableIntegrations(str, Enum):
    LORIS = "LORIS"


class Integration(InternalModel):
    integration_type: AvailableIntegrations


class IntegrationFilter(InternalModel):
    integration_types: list[AvailableIntegrations] | None
