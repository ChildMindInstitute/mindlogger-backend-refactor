import datetime
import uuid

from pydantic import EmailStr, validator

from apps.shared.domain import InternalModel, PublicModel
from apps.shared.domain.custom_validations import lowercase
from apps.workspaces.domain.constants import Role


class SubjectCreate(InternalModel):
    applet_id: uuid.UUID
    email: EmailStr | None = None
    creator_id: uuid.UUID
    user_id: uuid.UUID | None = None
    language: str | None = None
    first_name: str
    last_name: str
    secret_user_id: str
    nickname: str | None = None
    is_deleted: bool = False
    tag: str | None = None
    integration_source: str | None = None


class Subject(SubjectCreate):
    id: uuid.UUID
    meta: dict | None = None


class SubjectRespondent(PublicModel):
    id: uuid.UUID | None
    respondent_access_id: uuid.UUID
    subject_id: uuid.UUID
    relation: str
    user_id: uuid.UUID


class SubjectRelationCreate(PublicModel):
    relation: str


class SubjectBase(PublicModel):
    id: uuid.UUID | None
    applet_id: uuid.UUID
    email: EmailStr | None
    creator_id: uuid.UUID
    user_id: uuid.UUID | None
    tag: str | None


class SubjectCreateRequest(PublicModel):
    applet_id: uuid.UUID
    language: str
    first_name: str
    last_name: str
    secret_user_id: str
    nickname: str | None
    email: EmailStr | None
    tag: str | None

    _email_lower = validator("email", pre=True, allow_reuse=True)(lowercase)


class SubjectCreateResponse(SubjectCreateRequest):
    id: uuid.UUID | None
    creator_id: uuid.UUID
    user_id: uuid.UUID | None


class SubjectFull(SubjectBase):
    subjects: list[SubjectRespondent]


class SubjectUpdateRequest(PublicModel):
    secret_user_id: str
    nickname: str | None
    tag: str | None


class SubjectDeleteRequest(PublicModel):
    delete_answers: bool


class SubjectReadResponse(SubjectUpdateRequest):
    id: uuid.UUID
    last_seen: datetime.datetime | None
    applet_id: uuid.UUID
    user_id: uuid.UUID | None
    first_name: str
    last_name: str


class SubjectReadResponseWithDataAccess(SubjectReadResponse):
    team_member_can_view_data: bool = False
    roles: list[Role]


class TargetSubjectByRespondentResponse(SubjectReadResponseWithDataAccess):
    submission_count: int = 0
    currently_assigned: bool = False


class SubjectRelation(InternalModel):
    source_subject_id: uuid.UUID
    target_subject_id: uuid.UUID
    relation: str
    meta: dict | None
