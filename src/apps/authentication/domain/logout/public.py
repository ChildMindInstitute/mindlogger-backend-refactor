from apps.shared.domain import PublicModel


class UserLogoutRequest(PublicModel):
    device_id: str
