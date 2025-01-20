import json

from pydantic import BaseModel

from apps.integrations.db.schemas import IntegrationsSchema


class ProlificIntegration(BaseModel):
    api_key: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        configuration = json.loads(schema.configuration.replace("'", '"'))
        return cls(api_key=configuration["api_key"])

    def __repr__(self):
        return "ProlificIntegration()"
