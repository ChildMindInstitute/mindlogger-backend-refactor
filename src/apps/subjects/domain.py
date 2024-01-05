import uuid

from pydantic import EmailStr

from apps.shared.domain import InternalModel, PublicModel


class Subject(InternalModel):
    id: uuid.UUID
    applet_id: uuid.UUID
    email: EmailStr
    creator_id: uuid.UUID
    user_id: uuid.UUID


class SubjectRespondent(InternalModel):
    id: uuid.UUID
    respondent_access_id: uuid.UUID
    subject_id: uuid.UUID
    relation: str


class SubjectCreate(PublicModel):
    applet_id: uuid.UUID
    email: EmailStr
    creator_id: uuid.UUID
    user_id: uuid.UUID
    respondent_access_id: uuid.UUID
    relation: str


class SubjectFull(SubjectCreate):
    id: uuid.UUID
