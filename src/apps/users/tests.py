from apps.shared.test import BaseTest, rollback
from apps.users.domain import UserCreate
from apps.users.services import UsersCRUD


class TestUser(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    @rollback
    async def test_creating_user(self):
        user = UserCreate(
            email="qwe@mail.ru",
            full_name="tom isaak",
            hashed_password="qweqweqwe",
        )
        user, _ = await UsersCRUD().save_user(user)
        existed_user = await UsersCRUD().get_by_id(1)
        assert user.id == 2
        assert existed_user.id == 1
        assert existed_user.full_name == "Tom Isaak"

    @rollback
    async def test_checking_fixture_count(self):
        count = await UsersCRUD().count()
        assert count == 1
