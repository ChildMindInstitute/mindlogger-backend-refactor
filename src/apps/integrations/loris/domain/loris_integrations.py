import uuid

from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations
from apps.shared.domain import InternalModel


class IntegrationMeta(InternalModel):
    hostname: str
    username: str
    password: str
    project: str | None


class Integrations(InternalModel):
    applet_id: uuid.UUID
    type: AvailableIntegrations
    configuration: IntegrationMeta

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        return cls(applet_id=schema.applet_id, type=schema.type, configuration=schema.configuration)


class IntegrationsCreate(InternalModel):
    applet_id: uuid.UUID
    hostname: str
    username: str
    password: str
