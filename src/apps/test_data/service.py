import random
import string
import uuid
from datetime import date, timedelta

from apps.activities.domain.activity_create import (
    ActivityCreate,
    ActivityItemCreate,
)
from apps.activities.domain.response_type_config import (
    ChoiceConfig,
    ResponseType,
    TextConfig,
)
from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.applets.domain.applet_create import AppletCreate
from apps.applets.service import AppletService
from apps.schedule.domain.constants import PeriodicityType, TimerType
from apps.schedule.domain.schedule import EventRequest, PeriodicityRequest
from apps.schedule.service import ScheduleService


class TestDataService:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id

    async def create_applet(self):
        applet_create = self._generate_applet()
        applet = await AppletService(self.user_id).create(applet_create)

        await self._create_events(
            applet_id=applet.id,
            activity_ids=[activity.id for activity in applet.activities],
            flow_ids=[flow.id for flow in applet.activity_flows],
        )
        return applet

    @staticmethod
    def random_string(length=10):
        letters = string.ascii_letters
        return "".join(random.choice(letters) for _ in range(length))

    def random_image(self):
        return f"{self.random_string()}.jpg"

    @staticmethod
    def random_boolean():
        return random.choice([True, False])

    def _generate_applet(self) -> AppletCreate:
        activities = self._generate_activities()
        activity_flows = self._generate_activity_flows_from_activities(
            activities
        )
        applet_create = AppletCreate(
            display_name=self.random_string(),
            description=dict(
                en=self.random_string(50), fr=self.random_string(50)
            ),
            about=dict(en=self.random_string(50), fr=self.random_string(50)),
            image=self.random_string(),
            watermark=self.random_string(),
            theme_id=None,
            report_server_ip="",
            report_public_key="",
            report_recipients=[],
            report_include_user_id=False,
            report_include_case_id=False,
            report_email_body="",
            activities=activities,
            activity_flows=activity_flows,
        )

        return applet_create

    def _generate_activities(self, count=10) -> list[ActivityCreate]:
        activities = []
        for _ in range(count):
            items = self._generate_activity_items()
            activities.append(
                ActivityCreate(
                    name=self.random_string(),
                    key=uuid.uuid4(),
                    description=dict(
                        en=self.random_string(), fr=self.random_string()
                    ),
                    splash_screen=self.random_image(),
                    image=self.random_image(),
                    show_all_at_once=self.random_boolean(),
                    is_skippable=self.random_boolean(),
                    is_reviewable=self.random_boolean(),
                    response_is_editable=self.random_boolean(),
                    items=items,
                    is_hidden=self.random_boolean(),
                )
            )

        return activities

    def _generate_activity_flows_from_activities(
        self, activities: list[ActivityCreate], count=10
    ) -> list[FlowCreate]:
        flows = []
        for _ in range(count):
            flow_items = self._generate_flow_items(activities)
            flows.append(
                FlowCreate(
                    name=self.random_string(),
                    description=dict(
                        en=self.random_string(), fr=self.random_string()
                    ),
                    is_single_report=self.random_boolean(),
                    hide_badge=self.random_boolean(),
                    items=flow_items,
                    is_hidden=self.random_boolean(),
                )
            )
        return flows

    def _generate_activity_items(self, count=10) -> list[ActivityItemCreate]:
        items = []
        for _ in range(count):
            items.append(
                ActivityItemCreate(
                    header_image=self.random_image(),
                    question=dict(
                        en=self.random_string(), fr=self.random_string()
                    ),
                    response_type=ResponseType.TEXT,
                    answers=[],
                    config=self._generate_response_type_config(
                        ResponseType.TEXT
                    ),
                    skippable_item=self.random_boolean(),
                    remove_availability_to_go_back=self.random_boolean(),
                )
            )
        return items

    def _generate_response_type_config(self, type_: ResponseType):
        if type_ == ResponseType.TEXT:
            return TextConfig(
                max_response_length=random.randint(10, 100),
                correct_answer_required=self.random_boolean(),
                correct_answer=self.random_boolean(),
                numerical_response_required=self.random_boolean(),
                response_data_identifier=self.random_boolean(),
                response_required=self.random_boolean(),
            )
        elif type_ == ResponseType.CHOICE:
            return ChoiceConfig(
                set_alert=self.random_boolean(),
                option_score=self.random_boolean(),
                randomize_response_options=self.random_boolean(),
            )

    def _generate_flow_items(
        self, activities: list[ActivityCreate]
    ) -> list[FlowItemCreate]:
        items = []
        for index in random.sample(
            range(len(activities)), random.randint(1, len(activities))
        ):
            items.append(FlowItemCreate(activity_key=activities[index].key))

        return items

    async def _create_events(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID] | None = None,
        flow_ids: list[uuid.UUID] | None = None,
    ):
        # create events for activities
        events = []
        if activity_ids:
            for activity_id in activity_ids:
                schedule = self._generate_event_request(
                    activity_id=activity_id, flow_id=None
                )
                event = await ScheduleService().create_schedule(
                    schedule=schedule,
                    applet_id=applet_id,
                )
                events.append(event)

        # create events for flows
        if flow_ids:
            for flow_id in flow_ids:
                schedule = self._generate_event_request(
                    activity_id=None, flow_id=flow_id
                )
                event = await ScheduleService().create_schedule(
                    schedule=schedule,
                    applet_id=applet_id,
                )
                events.append(event)

        return events

    def _generate_event_request(
        self,
        activity_id: uuid.UUID | None = None,
        flow_id: uuid.UUID | None = None,
    ):
        return EventRequest(
            start_time="00:00:00",
            end_time="23:59:59",
            all_day=self.random_boolean(),
            access_before_schedule=self.random_boolean(),
            one_time_completion=self.random_boolean(),
            timer=timedelta(minutes=random.randint(1, 10)),
            timer_type=TimerType.not_set,
            periodicity=PeriodicityRequest(
                type=PeriodicityType.monthly,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=random.randint(30, 90)),
                interval=random.randint(1, 30),
            ),
            user_id=None,
            activity_id=activity_id if activity_id else None,
            flow_id=flow_id if flow_id else None,
        )
