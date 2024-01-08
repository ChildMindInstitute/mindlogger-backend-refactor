import uuid

from pydantic import EmailStr

from apps.shared.domain import InternalModel, PublicModel


class Subject(InternalModel):
    id: uuid.UUID | None
    applet_id: uuid.UUID
    email: EmailStr | None
    creator_id: uuid.UUID
    user_id: uuid.UUID
    language: str | None


class SubjectRespondent(InternalModel):
    id: uuid.UUID
    respondent_access_id: uuid.UUID
    subject_id: uuid.UUID
    relation: str


class SubjectCreate(PublicModel):
    applet_id: uuid.UUID
    email: EmailStr
    creator_id: uuid.UUID
    user_id: uuid.UUID | None
    respondent_access_id: uuid.UUID
    relation: str


class SubjectCreateRequest(InternalModel):
    applet_id: uuid.UUID
    language: str


class SubjectFull(SubjectCreate):
    id: uuid.UUID
