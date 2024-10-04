import json

from apps.integrations.db.schemas import IntegrationsSchema
from apps.shared.domain import InternalModel, PublicModel


class LorisIntegration(InternalModel):
    hostname: str
    username: str
    password: str
    project: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_loris_integration_dict = json.loads(schema.configuration.replace("'", '"'))
        new_loris_integration = cls(
            hostname=new_loris_integration_dict["hostname"],
            username=new_loris_integration_dict["username"],
            password=new_loris_integration_dict["password"],
            project=new_loris_integration_dict["project"],
        )
        return new_loris_integration

    def __repr__(self):
        return "LorisIntegration()"


class LorisIntegrationPublic(PublicModel):
    hostname: str
    username: str
    project: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        new_loris_integration_dict = json.loads(schema.configuration.replace("'", '"'))
        new_loris_integration = cls(
            hostname=new_loris_integration_dict["hostname"],
            username=new_loris_integration_dict["username"],
            project=new_loris_integration_dict["project"],
        )
        return new_loris_integration

    def __repr__(self):
        return "LorisIntegrationPublic()"
