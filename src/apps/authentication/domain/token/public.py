from apps.shared.domain import PublicModel
from config import settings


class Token(PublicModel):
    """This class is a public data model we send to the user."""

    access_token: str
    refresh_token: str
    token_type: str = settings.authentication.token_type
