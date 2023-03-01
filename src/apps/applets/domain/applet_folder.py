import uuid

from apps.shared.domain import InternalModel

__all__ = ["AppletFolder"]


class AppletFolder(InternalModel):
    applet_id: uuid.UUID
    folder_id: uuid.UUID | None
