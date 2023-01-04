from apps.shared.domain import PublicModel


class RefreshAccessTokenRequest(PublicModel):
    refresh_token: str
