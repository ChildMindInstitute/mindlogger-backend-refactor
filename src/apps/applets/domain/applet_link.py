from apps.shared.domain import InternalModel, PublicModel


class AppletLink(PublicModel):
    link: str | None


class CreateAccessLink(InternalModel):
    require_login: bool
