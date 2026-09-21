import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.domain.token import Token
from apps.authentication.services.rotation import TokenRotationService
from apps.users.domain import User


class TestTokenRotationService:
    async def test_store_and_get_rotation_replacement(self, session: AsyncSession):
        service = TokenRotationService(session)
        old_jti = str(uuid.uuid4())
        pair = Token(access_token="access-abc", refresh_token="refresh-def")

        await service.store_rotation_record(old_jti, pair)
        replacement = await service.get_rotation_replacement(old_jti)

        assert replacement is not None
        assert replacement.access_token == "access-abc"
        assert replacement.refresh_token == "refresh-def"

    async def test_get_rotation_replacement_missing_returns_none(self, session: AsyncSession):
        service = TokenRotationService(session)
        assert await service.get_rotation_replacement(str(uuid.uuid4())) is None

    async def test_revoke_family_and_is_family_revoked(self, session: AsyncSession, user: User):
        service = TokenRotationService(session)
        family_id = str(uuid.uuid4())

        assert await service.is_family_revoked(family_id) is False
        await service.revoke_family(family_id, user.id)
        assert await service.is_family_revoked(family_id) is True

    async def test_revoke_family_scoped_to_its_id(self, session: AsyncSession, user: User):
        service = TokenRotationService(session)
        revoked = str(uuid.uuid4())
        other = str(uuid.uuid4())

        await service.revoke_family(revoked, user.id)

        assert await service.is_family_revoked(revoked) is True
        assert await service.is_family_revoked(other) is False
