import datetime

from sqlalchemy.dialects.postgresql import insert

from apps.authentication.db.schemas import TokenBlacklistSchema
from apps.authentication.domain.token import InternalToken, TokenPurpose
from infrastructure.database import BaseCRUD


class TokenBlacklistCRUD(BaseCRUD):
    schema_class = TokenBlacklistSchema

    async def create(self, token: InternalToken, type_: TokenPurpose):
        """Blacklist a token.

        Uses ``ON CONFLICT (jti) DO NOTHING`` so that concurrent revocations of
        the same token (browser tabs sharing a session logging out together) are
        idempotent — the row already existing is the outcome the caller asked for.
        """
        query = (
            insert(TokenBlacklistSchema)
            .values(
                jti=token.payload.jti,
                user_id=token.payload.sub,
                exp=datetime.datetime.fromtimestamp(token.payload.exp, datetime.UTC).replace(tzinfo=None),
                type=type_,
                rjti=token.payload.rjti,
            )
            .on_conflict_do_nothing(index_elements=[TokenBlacklistSchema.jti])
        )
        await self._execute(query)

    async def exists(self, token: InternalToken) -> bool:
        return await self.exist_by_key("jti", token.payload.jti)
