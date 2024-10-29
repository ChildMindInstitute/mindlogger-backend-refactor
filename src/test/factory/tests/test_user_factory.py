from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.test import BaseTest
from test.factory.user_factory import create_user


class TestUserFactory(BaseTest):
    async def test_create_user(self, session: AsyncSession):
        user = await create_user(session)
        assert user
        assert user.id

    async def test_create_user_with_attributes(self, session: AsyncSession):
        user = await create_user(session, email=EmailStr("test@test.com"))
        assert user.email_encrypted == "test@test.com"
