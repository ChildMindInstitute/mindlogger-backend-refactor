import allure
from sqlalchemy import func, select

from apps.users import User, UserSchema


@allure.epic("Validate Test Suite")
@allure.feature("Tests")
@allure.severity(allure.severity_level.CRITICAL)
@allure.issue("M2-11172")
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

    async def test_create_many_users(self, phineas_user: User, ferb_user: User, doofenshmirtz_user: User):
        assert phineas_user.id != ferb_user.id
        assert phineas_user.id != doofenshmirtz_user.id
        assert ferb_user.id != doofenshmirtz_user.id

        assert phineas_user.email != doofenshmirtz_user.email
        assert ferb_user.email != doofenshmirtz_user.email
        assert phineas_user.email != ferb_user.email

        assert phineas_user.hashed_password != doofenshmirtz_user.hashed_password
        assert ferb_user.hashed_password != doofenshmirtz_user.hashed_password
        assert phineas_user.hashed_password != ferb_user.hashed_password
