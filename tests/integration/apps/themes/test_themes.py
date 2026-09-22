import pytest
import allure
from polyfactory.factories.pydantic_factory import ModelFactory

from apps.users import User

fixtures = ["apps/themes/fixtures/themes.json"]

class UserFactory(ModelFactory[User]): ...

@allure.epic("Themes")
@allure.severity(allure.severity_level.MINOR)
class TestThemes:
    login_url = "/auth/login"
    list_url = "/themes"

    @allure.title("Test Themes")
    # @pytest.mark.db_fixtures(fixtures)
    async def test_themes_list(self, create_authorized_client):
        user = UserFactory.build()
        client = create_authorized_client(user)
        # response = await client.get(self.list_url)

        # assert response.status_code == 200
        # assert isinstance(response.json()["result"], list)

        assert True