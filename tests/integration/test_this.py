import allure
from sqlalchemy import func, select

from apps.users import UserSchema


@allure.epic("Test")
@allure.severity(allure.severity_level.CRITICAL)
class TestTestSuite:
    """Sanity test some fixtures in the test suite"""

    @allure.title("Test User Create")
    @allure.description("Test that there is a user in the database")
    async def test_user_create(self, db_session, ferb_user):
        length = await self._get_user_count(db_session)
        assert length == 1

    @allure.title("Test User is cleaned up")
    @allure.description("Test that there are no users in the database")
    async def test_db_empty(self, db_session):
        length = await self._get_user_count(db_session)
        assert length == 0

    async def _get_user_count(self, db_session):
        length = await db_session.scalar(select(func.count()).select_from(UserSchema))
        return length
