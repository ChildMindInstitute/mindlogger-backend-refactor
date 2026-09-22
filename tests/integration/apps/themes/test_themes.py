import pytest
import allure
from polyfactory.factories.pydantic_factory import ModelFactory
from sqlalchemy import text, func, select

from apps.users import User, UserSchema, UsersCRUD
from apps.users.domain import UserCreate
from apps.users.services.user import UserService
from infrastructure.database import atomic

fixtures = ["apps/themes/fixtures/themes.json"]

class UserFactory(ModelFactory[User]): ...
class UserCreateFactory(ModelFactory[UserCreate]): ...

@allure.epic("Themes")
@allure.severity(allure.severity_level.MINOR)
class TestThemes:
    login_url = "/auth/login"
    list_url = "/themes"

    @allure.title("Test Themes")
    @pytest.mark.db_fixtures(fixtures)
    async def test_themes_list(self, create_authorized_client, db_session):
        user = UserCreateFactory.build(password = "QWERTy65@2%sfd42fwe!")
        async with atomic(db_session):
            new_user = await UserService(db_session).create_user(user)
        length = await db_session.scalar(select(func.count()).select_from(UserSchema))
        assert length == 1
        
        async with create_authorized_client(new_user) as client:
            response = await client.get(self.list_url)

        assert response.status_code == 200
        assert isinstance(response.json()["result"], list)

        

    async def test_db_empty(self, db_session):
        length = await db_session.scalar(select(func.count()).select_from(UserSchema))
        assert length == 0
