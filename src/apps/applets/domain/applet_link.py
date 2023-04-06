from apps.shared.domain import InternalModel, PublicModel


class AppletLink(PublicModel):
    link: str | None
    require_login: bool = False


class CreateAccessLink(InternalModel):
    require_login: bool
