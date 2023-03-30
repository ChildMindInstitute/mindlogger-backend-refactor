import random
import string
import uuid
from datetime import datetime, timedelta

from apps.activities.domain.activity_create import (
    ActivityCreate,
    ActivityItemCreate,
)
from apps.activities.domain.response_type_config import (
    ResponseType,
    SingleSelectionConfig,
    TextConfig,
)
from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.applets.domain.applet_create import AppletCreate
from apps.applets.service import AppletService
from apps.schedule.domain.constants import PeriodicityType, TimerType
from apps.schedule.domain.schedule import EventRequest, PeriodicityRequest
from apps.schedule.service import ScheduleService
from apps.shared.query_params import QueryParams
from apps.test_data.domain import AnchorDateTime


class TestDataService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session
        self.timer_options = [
            {"type": TimerType.TIMER, "value": timedelta(minutes=195)},
            {"type": TimerType.IDLE, "value": timedelta(minutes=1)},
            {"type": TimerType.TIMER, "value": timedelta(minutes=1)},
            {"type": TimerType.IDLE, "value": timedelta(minutes=195)},
            {"type": TimerType.TIMER, "value": timedelta(minutes=195)},
            {"type": TimerType.IDLE, "value": timedelta(minutes=195)},
        ]

    async def create_applet(self, anchor_datetime: AnchorDateTime):
        # delete applets with suffix '-generated'

        old_applets = await AppletService(
            self.session, self.user_id
        ).get_list_by_single_language(
            language="en", query_params=QueryParams(filters={"roles": "ADMIN"})
        )

        if old_applets:
            for old_applet in old_applets:
                if old_applet.display_name.endswith("-generated"):
                    await AppletService(
                        self.session, self.user_id
                    ).delete_applet_by_id(old_applet.id)

        applet_create = self._generate_applet()
        applet = await AppletService(self.session, self.user_id).create(
            applet_create
        )

        await self._create_activity_events(
            applet_id=applet.id,
            activity_ids=[activity.id for activity in applet.activities],
            anchor_datetime=anchor_datetime.anchor_date_time,
        )
        await self._create_flow_events(
            applet_id=applet.id,
            flow_ids=[flow.id for flow in applet.activity_flows],
            anchor_datetime=anchor_datetime.anchor_date_time,
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
            display_name=f"{self.random_string()}-password-"
            "Test1234!-generated",
            # noqa: E501
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
            password="Test1234!",
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
                    name=self.random_string(),
                    question=dict(
                        en=self.random_string(), fr=self.random_string()
                    ),
                    response_type=ResponseType.TEXT,
                    response_values=None,
                    config=self._generate_response_type_config(
                        ResponseType.TEXT
                    ),
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
                skippable_item=self.random_boolean(),
                remove_back_button=self.random_boolean(),
            )
        elif type_ == ResponseType.SINGLESELECT:
            return SingleSelectionConfig(
                remove_back_button=self.random_boolean(),
                skippable_item=self.random_boolean(),
                randomize_options=self.random_boolean(),
                timer=0,
                add_scores=self.random_boolean(),
                set_alerts=self.random_boolean(),
                set_palette=self.random_boolean(),
                add_tooltip=self.random_boolean(),
                additional_response_option={
                    "text_input_option": False,
                    "text_input_required": False,
                },
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

    async def _create_activity_events(
        self,
        anchor_datetime: datetime,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID] | None = None,
    ):
        # create events for activities
        events = []
        if activity_ids:
            events = await self._create_events(
                applet_id=applet_id,
                entity_ids=activity_ids,
                is_activity=True,
                anchor_datetime=anchor_datetime,
            )
        return events

    async def _create_flow_events(
        self,
        anchor_datetime: datetime,
        applet_id: uuid.UUID,
        flow_ids: list[uuid.UUID] | None = None,
    ):
        # create events for flows
        events = []
        if flow_ids:
            events = await self._create_events(
                applet_id=applet_id,
                entity_ids=flow_ids,
                is_activity=False,
                anchor_datetime=anchor_datetime,
            )
        return events

    def _generate_event_request(
        self,
        activity_id: uuid.UUID | None = None,
        flow_id: uuid.UUID | None = None,
    ):
        return EventRequest(
            start_time="00:00:00",
            end_time="23:59:59",
            access_before_schedule=False,
            one_time_completion=self.random_boolean(),
            timer=timedelta(minutes=random.randint(1, 10)),
            timer_type=TimerType.NOT_SET,
            periodicity=PeriodicityRequest(
                type=PeriodicityType.ALWAYS,
                start_date=None,
                end_date=None,
                selected_date=None,
            ),
            respondent_id=None,
            activity_id=activity_id if activity_id else None,
            flow_id=flow_id if flow_id else None,
        )

    def _get_generated_event(
        self,
        is_activity: bool,
        entity_ids: list[uuid.UUID],
        current_entity_index: int,
    ):

        if is_activity:
            default_event = self._generate_event_request(
                activity_id=entity_ids[current_entity_index],
            )
        else:
            default_event = self._generate_event_request(
                flow_id=entity_ids[current_entity_index],
            )
        return default_event

    async def _create_events(
        self,
        applet_id: uuid.UUID,
        anchor_datetime: datetime,
        entity_ids: list[uuid.UUID] | None = None,
        is_activity: bool = True,
    ):
        events = []
        if entity_ids:
            current_entity_index = 0
            # first event always available and allow_access_before_schedule false # noqa: E501
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )
            default_event.access_before_schedule = False
            default_event = self._set_timer(
                default_event, current_entity_index
            )

            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )
            # second event always available and allow_access_before_schedule true # noqa: E501
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )
            default_event.access_before_schedule = True
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # third event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )
            default_event.periodicity.start_date = (
                anchor_datetime.date() - timedelta(days=5)
            )
            default_event.periodicity.end_date = (
                anchor_datetime.date() - timedelta(days=3)
            )
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fourth event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )
            default_event.periodicity.start_date = (
                anchor_datetime.date() - timedelta(days=2)
            )
            default_event.periodicity.end_date = (
                anchor_datetime.date() + timedelta(days=2)
            )
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fifth event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )
            default_event.periodicity.start_date = (
                anchor_datetime.date() + timedelta(days=2)
            )
            default_event.periodicity.end_date = (
                anchor_datetime.date() + timedelta(days=5)
            )
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # sixth event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.type = PeriodicityType.DAILY

            default_event.start_time = (
                anchor_datetime + timedelta(minutes=60)
            ).time()
            default_event.end_time = (
                anchor_datetime + timedelta(minutes=180)
            ).time()

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # seventh event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.type = PeriodicityType.DAILY
            default_event.start_time = (
                anchor_datetime + timedelta(minutes=60)
            ).time()
            default_event.end_time = (
                anchor_datetime + timedelta(minutes=180)
            ).time()
            default_event.access_before_schedule = True

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # eighth event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.type = PeriodicityType.DAILY
            default_event.start_time = (
                anchor_datetime - timedelta(minutes=180)
            ).time()
            default_event.end_time = (
                anchor_datetime - timedelta(minutes=60)
            ).time()

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # ninth event daily
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.type = PeriodicityType.DAILY
            default_event.start_time = (
                anchor_datetime - timedelta(minutes=180)
            ).time()
            default_event.end_time = (
                anchor_datetime + timedelta(minutes=180)
            ).time()

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # tenth event weekly
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.selected_date = (
                anchor_datetime.date() - timedelta(days=2)
            )
            default_event.periodicity.type = PeriodicityType.WEEKLY

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # eleventh event weekly
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.WEEKLY
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # twelfth event weekly
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.selected_date = (
                anchor_datetime.date() + timedelta(days=2)
            )
            default_event.periodicity.type = PeriodicityType.WEEKLY
            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # thirteenth event montly
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.MONTHLY

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fourteenth event weekdays
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.type = PeriodicityType.WEEKDAYS

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fifteenth event once
            current_entity_index = self._increment_index(
                current_entity_index, len(entity_ids)
            )
            default_event = self._get_generated_event(
                is_activity,
                entity_ids,
                current_entity_index,
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.ONCE

            default_event = self._set_timer(
                default_event, current_entity_index
            )
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

        return events

    def _increment_index(self, index: int, length: int):
        if index == length - 1:
            return 0
        return index + 1

    def _set_timer(self, event: EventRequest, index: int):
        timer_data = self._get_timer_option(index)
        event.timer_type = timer_data["type"]
        event.timer = timer_data["value"]
        return event

    def _get_timer_option(self, index: int):
        # get from option index mod length
        return self.timer_options[index % len(self.timer_options)]
