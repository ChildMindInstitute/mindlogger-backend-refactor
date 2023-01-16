import datetime

from apps.shared.domain import InternalModel, PublicModel


class User(InternalModel):
    full_name: str


class UserPublic(InternalModel):
    full_name: str


class History(InternalModel):
    version: str
    creator: User
    created_at: datetime.datetime


class PublicHistory(PublicModel):
    version: str
    creator: UserPublic
    created_at: datetime.datetime
