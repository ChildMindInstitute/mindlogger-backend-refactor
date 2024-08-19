import json
import uuid
from enum import Enum
from typing import Union

from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.loris.domain.loris_integrations import LorisIntegration
from apps.shared.domain import InternalModel


class AvailableIntegrations(str, Enum):
    LORIS = "LORIS"
    FUTURE = "FUTURE"


class FutureIntegration(InternalModel):
    endpoint: str
    api_key: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_future_integration_dict = json.loads(schema.configuration.replace("'", '"'))
        new_future_integration_dict["api_key"] = "*****"

        new_future_integration = cls(
            endpoint=new_future_integration_dict["endpoint"],
            api_key=new_future_integration_dict["api_key"],
        )
        return new_future_integration

class Integration(InternalModel):
    integration_type: AvailableIntegrations
    applet_id: uuid.UUID
    configuration: Union[LorisIntegration, FutureIntegration]

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_integration = cls(
            applet_id=schema.applet_id,
            integration_type=schema.type,
            configuration=schema.configuration
        )
        return new_integration


class IntegrationFilter(InternalModel):
    integration_types: list[AvailableIntegrations] | None
