from apps.shared.domain import InternalModel


class UserLogoutRequest(InternalModel):
    device_id: str | None = None
