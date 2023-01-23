from apps.shared.test import BaseTest
from infrastructure.database import transaction
from starlette import status
from apps.schedule.router import router as schedule_router


class TestSchedule(BaseTest):
    schedule_create_url = schedule_router.url_path_for("schedule_create")
    schedule_get_all_url = schedule_router.url_path_for("schedule_get_all")
    schedule_get_by_id_url = schedule_router.url_path_for("schedule_get_by_id")
    schedule_delete_url = schedule_router.url_path_for("schedule_delete")

    create_request_user = UserCreateRequestFactory.build()
    user_update_request = UserUpdateRequestFactory.build()

    @transaction.rollback
    async def test_user_create(self):
        # Creating new user
        response = await self.client.post(
            self.user_create_url, data=self.create_request_user.dict()
        )
        # Get  created user by email
        created_user: User = await UsersCRUD().get_by_email(
            self.create_request_user.email
        )

        public_user = PublicUser(**created_user.dict())

        expected_result: Response[PublicUser] = Response(result=public_user)

        count = await UsersCRUD().count()

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == expected_result.dict(by_alias=True)
        assert count == expected_result.result.id
