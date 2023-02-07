from apps.shared.domain import InternalModel, PublicModel


class AppletName(InternalModel):
    name: str
    exclude_applet_id: int | None


class AppletUniqueName(PublicModel):
    name: str
