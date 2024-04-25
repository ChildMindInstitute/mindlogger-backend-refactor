import datetime
import uuid

from apps.shared.domain import InternalModel, PublicModel


class User(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class UserPublic(PublicModel):
    first_name: str
    last_name: str


class Version(InternalModel):
    version: str
    created_at: datetime.datetime


class VersionPublic(PublicModel):
    version: str
    created_at: datetime.datetime


class History(Version):
    creator: User


class PublicHistory(VersionPublic):
    creator: UserPublic
