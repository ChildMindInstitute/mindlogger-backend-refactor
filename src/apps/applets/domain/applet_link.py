from apps.shared.domain import InternalModel, PublicModel


class AppletLink(InternalModel):
    link: str
    require_login: bool


class CreateAccessLink(InternalModel):
    require_login: bool
