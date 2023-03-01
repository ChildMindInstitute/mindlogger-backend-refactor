import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel


class User(InternalModel):
    id: uuid.UUID
    full_name: str


class UserPublic(PublicModel):
    full_name: str


class History(InternalModel):
    version: str
    creator: User
    created_at: datetime.datetime


class PublicHistory(PublicModel):
    version: str
    creator: UserPublic
    created_at: datetime.datetime
