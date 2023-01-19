from apps.authentication.domain.token import Token
from apps.shared.domain import PublicModel
from apps.users.domain import PublicUser


class UserLogin(PublicModel):
    token: Token
    user: PublicUser
