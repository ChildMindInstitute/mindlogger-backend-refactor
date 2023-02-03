from apps.shared.domain import InternalModel, PublicModel

__all__ = ["FolderCreate", "Folder", "FolderUpdate", "FolderPublic"]


class FolderCreate(InternalModel):
    name: str


class Folder(InternalModel):
    id: int
    creator_id: int
    name: str


class FolderUpdate(InternalModel):
    name: str


class FolderPublic(PublicModel):
    id: int
    name: str
