import json
import uuid
from enum import Enum
from typing import Any

from apps.integrations.db.schemas import IntegrationsSchema
from apps.shared.domain import InternalModel, PublicModel


class AvailableIntegrations(str, Enum):
    LORIS = "LORIS"
    FUTURE = "FUTURE"


class FutureIntegration(InternalModel):
    endpoint: str
    api_key: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_future_integration_dict = json.loads(schema.configuration.replace("'", '"'))
        new_future_integration = cls(
            endpoint=new_future_integration_dict["endpoint"],
            api_key=new_future_integration_dict["api_key"],
        )
        return new_future_integration

    def __repr__(self):
        return "FutureIntegration()"


class FutureIntegrationPublic(PublicModel):
    endpoint: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_future_integration_dict = json.loads(schema.configuration.replace("'", '"'))
        new_future_integration = cls(
            endpoint=new_future_integration_dict["endpoint"],
        )
        return new_future_integration

    def __repr__(self):
        return "FutureIntegrationPublic()"


class Integration(InternalModel):
    integration_type: AvailableIntegrations
    applet_id: uuid.UUID
    configuration: Any

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_integration = cls(
            applet_id=schema.applet_id, integration_type=schema.type, configuration=schema.configuration
        )
        return new_integration


class IntegrationFilter(InternalModel):
    integration_types: list[AvailableIntegrations] | None
