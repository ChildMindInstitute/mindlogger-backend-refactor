import allure

fixtures = ["apps/themes/fixtures/themes.json"]


@allure.epic("Themes")
@allure.severity(allure.severity_level.MINOR)
class TestThemes:
    login_url = "/auth/login"
    list_url = "/themes"

    @allure.title("Test Themes")
    async def test_themes_list(self, create_authorized_client, db_session, ferb_user):
        async with create_authorized_client(ferb_user) as client:
            response = await client.get(self.list_url)

        assert response.status_code == 200
        assert isinstance(response.json()["result"], list)
