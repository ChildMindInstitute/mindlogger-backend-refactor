import uuid


from apps.shared.domain import InternalModel


class AppletLibraryItem(InternalModel):
    applet_id_version: str
    id: uuid.UUID


class AppletLibrary(InternalModel):
    applet_id_version: str
    id: uuid.UUID
