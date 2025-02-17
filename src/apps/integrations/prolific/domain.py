import json

from pydantic import BaseModel

from apps.integrations.db.schemas import IntegrationsSchema
from apps.shared.domain.base import InternalModel


class ProlificIntegration(BaseModel):
    api_key: str

    @classmethod
    def from_schema(cls, schema: IntegrationsSchema):
        configuration = json.loads(schema.configuration.replace("'", '"'))
        return cls(api_key=configuration["api_key"])

    def __repr__(self):
        return "ProlificIntegration()"


class ProlificStudyValidation(InternalModel):
    accepted: bool


class ProlificUserInfo(InternalModel):
    prolific_pid: str
    study_id: str


class ProlificParamsActivityAnswer(InternalModel):
    prolific_pid: str
    session_id: str
    study_id: str


class ProlificAction(InternalModel):
    action: str


class ProlificCompletionCode(InternalModel):
    code: str
    code_type: str
    actions: list[ProlificAction]
    actor: str


class ProlificCompletionCodeList(InternalModel):
    completion_codes: list[ProlificCompletionCode]
