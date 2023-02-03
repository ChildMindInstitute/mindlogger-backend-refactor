from apps.shared.domain import InternalModel

__all__ = ["AppletFolder"]


class AppletFolder(InternalModel):
    applet_id: int
    folder_id: int | None
