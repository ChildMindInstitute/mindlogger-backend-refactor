import uuid

from apps.shared.domain import InternalModel, PublicModel

__all__ = ["FolderCreate", "Folder", "FolderUpdate", "FolderPublic"]


class FolderCreate(InternalModel):
    name: str


class Folder(InternalModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    name: str


class FolderUpdate(InternalModel):
    name: str


class FolderPublic(PublicModel):
    id: uuid.UUID
    name: str
