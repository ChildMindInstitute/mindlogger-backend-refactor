import uuid

from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain import User, UserCreate
from apps.users.services.user import UserService


async def create_user(session: AsyncSession, **kwargs) -> User:
    attrs = {
        "first_name": "Tester",
        "last_name": "Testerson",
        "email": EmailStr(f"test-{uuid.uuid4()}@mindlogger.com"),
        "password": "Test1234!",
    }
    attrs.update(kwargs)

    user = await UserService(session).create_user(UserCreate(**attrs))
    await session.commit()

    return user
