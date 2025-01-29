import datetime

from apps.authentication.crud import TokenBlacklistCRUD
from apps.authentication.domain.token import InternalToken, TokenPurpose

__all__ = ["TokensService"]


class TokensService:
    def __init__(self, session) -> None:
        self.session = session

    async def is_revoked(self, token: InternalToken) -> bool:
        return await TokenBlacklistCRUD(self.session).exists(token)

    async def revoke(self, token: InternalToken, type_: TokenPurpose) -> None:
        now = datetime.datetime.now(datetime.UTC)
        ttl = token.payload.exp - int(now.timestamp())
        if ttl > 1:
            revoked = await self.is_revoked(token)
            if not revoked:
                await TokenBlacklistCRUD(self.session).create(token, type_)
