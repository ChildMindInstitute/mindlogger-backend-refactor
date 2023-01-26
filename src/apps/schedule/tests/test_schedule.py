# from apps.shared.test import BaseTest
# from infrastructure.database import transaction
# from starlette import status
# from apps.schedule.router import router as schedule_router
# from apps.schedule.domain.schedule import Event
# from apps.schedule.service import ScheduleService
# from apps.schedule.tests.factories import EventRequestFactory


# class TestSchedule(BaseTest):
#     schedule_create_url = schedule_router.url_path_for("schedule_create")
#     schedule_get_all_url = schedule_router.url_path_for("schedule_get_all")
#     schedule_get_by_id_url = schedule_router.url_path_for("schedule_get_by_id") # noqa: E501
#     schedule_delete_url = schedule_router.url_path_for("schedule_delete")

#     create_request_schedule = EventRequestFactory.build()

#     @transaction.rollback
#     async def test_schedule_create(self):
#         pass
#         # use fixture
