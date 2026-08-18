import json
import uuid
from datetime import datetime, timedelta, timezone

from apps.authentication.crud import TokenBlacklistCRUD
from apps.authentication.domain.token import InternalToken, Token, TokenPayload, TokenPurpose
from apps.authentication.services.core import TokensService
from config import settings
from infrastructure.utility.redis_client import RedisCache

__all__ = ["TokenRotationService"]


class TokenRotationService:
    """Refresh-token rotation support for web/admin clients.

    Two responsibilities:
    - a short-lived Redis "grace record" mapping a just-rotated refresh token's jti to
      the replacement token pair, so the old token redeems idempotently for a brief window;
    - family revocation via the existing token blacklist, keyed by the family id, so a whole
      rotated chain can be killed at once (on reuse detection or logout).
    """

    def __init__(self, session) -> None:
        self.session = session
        self.redis_client = RedisCache()

    @staticmethod
    def _grace_key(old_jti: str) -> str:
        return f"token_rotation:{old_jti}"

    @staticmethod
    def _family_blacklist_jti(family_id: str) -> str:
        # Namespaced so a family-revocation row never collides with a real token jti
        # (the family id equals the login refresh token's jti, which itself gets
        # blacklisted on its first rotation).
        return f"family:{family_id}"

    async def get_rotation_replacement(self, old_jti: str) -> Token | None:
        raw = await self.redis_client.get(self._grace_key(old_jti))
        if not raw:
            return None
        data = json.loads(raw)
        return Token(access_token=data["access_token"], refresh_token=data["refresh_token"])

    async def store_rotation_record(self, old_jti: str, token: Token) -> None:
        await self.redis_client.set(
            self._grace_key(old_jti),
            json.dumps({"access_token": token.access_token, "refresh_token": token.refresh_token}),
            ex=settings.authentication.refresh_token.rotation_grace_seconds,
        )

    async def is_family_revoked(self, family_id: str) -> bool:
        return await TokenBlacklistCRUD(self.session).exist_by_key("jti", self._family_blacklist_jti(family_id))

    async def revoke_family(self, family_id: str, user_id: uuid.UUID) -> None:
        # Blacklist a synthetic row under the namespaced family jti, retained comfortably past
        # any live token in the family (refresh lifetime is the longest a token can survive).
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.authentication.refresh_token.expiration)
        family_token = InternalToken(
            payload=TokenPayload(sub=user_id, exp=int(expire.timestamp()), jti=self._family_blacklist_jti(family_id))
        )
        await TokensService(self.session).revoke(family_token, TokenPurpose.REFRESH)
