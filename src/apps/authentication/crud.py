import datetime

from apps.authentication.db.schemas import TokenBlacklistSchema
from apps.authentication.domain.token import InternalToken, TokenPurpose
from infrastructure.database import BaseCRUD


class TokenBlacklistCRUD(BaseCRUD):
    schema_class = TokenBlacklistSchema

    async def create(self, token: InternalToken, type_: TokenPurpose):
        await self._create(
            TokenBlacklistSchema(
                jti=token.payload.jti,
                user_id=token.payload.sub,
                exp=datetime.datetime.fromtimestamp(token.payload.exp, datetime.UTC).replace(tzinfo=None),
                type=type_,
                rjti=token.payload.rjti,
            )
        )

    async def exists(self, token: InternalToken) -> bool:
        return await self.exist_by_key("jti", token.payload.jti)
