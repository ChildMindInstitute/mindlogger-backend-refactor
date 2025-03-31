import random
import string
import uuid
from datetime import datetime, timedelta

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.domain.response_type_config import ResponseType
from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.base import Encryption
from apps.applets.service import AppletService
from apps.schedule.domain.constants import NotificationTriggerType, PeriodicityType, TimerType
from apps.schedule.domain.schedule import (
    EventRequest,
    NotificationSettingRequest,
    PeriodicityRequest,
    ReminderSettingRequest,
)
from apps.schedule.service import ScheduleService
from apps.shared.query_params import QueryParams
from apps.test_data.domain import AppletGeneration, image_url
from apps.workspaces.domain.constants import Role


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
        self.activity_item_options = [
            ResponseType.TEXT,
            ResponseType.SINGLESELECT,
            ResponseType.MULTISELECT,
            ResponseType.SLIDER,
        ]

    async def create_applet(self, applet_generation: AppletGeneration):
        applet_create = self._generate_applet(applet_generation.encryption)
        applet = await AppletService(self.session, self.user_id).create(applet_create)
        entity_ids = [{"id": activity.id, "is_activity": True} for activity in applet.activities]
        entity_ids.extend([{"id": flow.id, "is_activity": False} for flow in applet.activity_flows])

        await self._create_all_events(
            applet_id=applet.id,
            entity_ids=entity_ids,
            anchor_datetime=applet_generation.anchor_date_time,
        )
        return applet

    @staticmethod
    def random_string(length=10):
        letters = string.ascii_letters
        return "".join(random.choice(letters) for _ in range(length))

    @staticmethod
    def random_boolean():
        return random.choice([True, False])

    def _generate_applet(self, encryption: Encryption) -> AppletCreate:
        activities = self._generate_activities()
        activity_flows = self._generate_activity_flows_from_activities(activities)
        applet_create = AppletCreate(
            display_name=f"Applet-{self.random_string()}-generated",
            # noqa: E501
            description=dict(
                en=f"Applet description {self.random_string(50)}",
                fr=f"Applet description {self.random_string(50)}",
            ),
            about=dict(
                en=f"Applet about {self.random_string(50)}",
                fr=f"Applet about {self.random_string(50)}",
            ),
            encryption=encryption.dict(),
            image=image_url,
            watermark=image_url,
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

    def _generate_activities(self, count=5) -> list[ActivityCreate]:
        activities = []
        has_reviewable = False
        for index in range(count):
            items = self.generate_activity_items()
            is_reviewable = self.random_boolean()
            if has_reviewable:
                is_reviewable = False
            if is_reviewable:
                has_reviewable = True
            activities.append(
                ActivityCreate(
                    name=f"Activity {index + 1}",
                    key=uuid.uuid4(),
                    description=dict(
                        en=f"Activity {index + 1} desc {self.random_string()}",
                        fr=f"Activity {index + 1} desc {self.random_string()}",
                    ),
                    splash_screen=image_url,
                    image=image_url,
                    show_all_at_once=self.random_boolean(),
                    is_skippable=self.random_boolean(),
                    is_reviewable=is_reviewable,
                    response_is_editable=self.random_boolean(),
                    items=items,
                    is_hidden=self.random_boolean(),
                )
            )

        return activities

    def _generate_activity_flows_from_activities(self, activities: list[ActivityCreate], count=5) -> list[FlowCreate]:
        flows = []
        for index in range(count):
            flow_items = self._generate_flow_items(activities)
            flows.append(
                FlowCreate(
                    name=f"Flow {index + 1}",
                    description=dict(
                        en=f"Flow {index + 1} desc {self.random_string()}",
                        fr=f"Flow {index + 1} desc {self.random_string()}",
                    ),
                    is_single_report=self.random_boolean(),
                    hide_badge=self.random_boolean(),
                    items=flow_items,
                    is_hidden=self.random_boolean(),
                )
            )
        return flows

    def generate_activity_items(self, count=10) -> list[ActivityItemCreate]:
        items = []
        for index in range(count):
            response_config = self.generate_response_value_config(
                type_=self.activity_item_options[index % len(self.activity_item_options)]
            )

            items.append(
                ActivityItemCreate(
                    name=f"activity_item_{index + 1}",
                    question=dict(
                        en=f"Activity item question {self.random_string()}",
                        fr=f"Activity item question {self.random_string()}",
                    ),
                    response_type=self.activity_item_options[index % len(self.activity_item_options)],
                    response_values=response_config["response_values"],
                    config=response_config["config"],
                    is_hidden=self.random_boolean(),
                )
            )
        return items

    @staticmethod
    def generate_response_value_config(type_: ResponseType):
        result = dict()
        if type_ == ResponseType.TEXT:
            result["config"] = dict(
                max_response_length=200,
                correct_answer_required=False,
                correct_answer=None,
                numerical_response_required=False,
                response_data_identifier=False,
                response_required=False,
                remove_back_button=False,
                skippable_item=True,
            )

            result["response_values"] = None  # type: ignore  # noqa: E501

        elif type_ == ResponseType.SINGLESELECT:
            result["config"] = dict(
                remove_back_button=False,
                skippable_item=True,
                randomize_options=False,
                timer=None,
                add_scores=False,
                set_alerts=False,
                add_tooltip=False,
                set_palette=False,
                response_data_identifier=False,
                additional_response_option=dict(  # type: ignore  # noqa: E501
                    text_input_option=False,
                    text_input_required=False,
                ),
            )

            result["response_values"] = {
                "options": [  # type: ignore  # noqa: E501
                    {
                        "id": str(uuid.uuid4()),
                        "text": "option 1",
                        "image": None,
                        "score": None,
                        "tooltip": None,
                        "is_hidden": False,
                        "color": None,
                        "value": 0,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "text": "option 2",
                        "image": None,
                        "score": None,
                        "tooltip": None,
                        "is_hidden": False,
                        "color": None,
                        "value": 1,
                    },
                ]
            }

        elif type_ == ResponseType.MULTISELECT:
            result["config"] = dict(
                remove_back_button=False,
                skippable_item=True,
                randomize_options=False,
                timer=None,
                add_scores=False,
                set_alerts=False,
                add_tooltip=False,
                set_palette=False,
                additional_response_option=dict(  # type: ignore  # noqa: E501
                    text_input_option=False,
                    text_input_required=False,
                ),
            )

            result["response_values"] = {
                "options": [  # type: ignore  # noqa: E501
                    {
                        "id": str(uuid.uuid4()),
                        "text": "option 1",
                        "image": None,
                        "score": None,
                        "tooltip": None,
                        "is_hidden": False,
                        "color": None,
                        "value": 0,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "text": "option 2",
                        "image": None,
                        "score": None,
                        "tooltip": None,
                        "is_hidden": False,
                        "color": None,
                        "value": 1,
                    },
                ]
            }

        elif type_ == ResponseType.SLIDER:
            result["config"] = dict(
                add_scores=False,
                set_alerts=False,
                show_tick_marks=False,
                show_tick_labels=False,
                continuous_slider=False,
                timer=None,
                remove_back_button=False,
                skippable_item=True,
                additional_response_option=dict(  # type: ignore  # noqa: E501
                    text_input_option=False,
                    text_input_required=False,
                ),
            )

            result["response_values"] = {
                "min_value": 0,
                "max_value": 10,
                "min_label": "min label",  # type: ignore  # noqa: E501
                "max_label": "max label",  # type: ignore  # noqa: E501
                "min_image": None,
                "max_image": None,
                "scores": None,
            }

        return result

    def _generate_flow_items(self, activities: list[ActivityCreate]) -> list[FlowItemCreate]:
        items = []
        for index in random.sample(range(len(activities)), random.randint(1, len(activities))):
            items.append(FlowItemCreate(activity_key=activities[index].key))

        return items

    async def _create_all_events(
        self,
        anchor_datetime: datetime,
        applet_id: uuid.UUID,
        entity_ids: list[dict] | None = None,
    ):
        # create events for activities
        events = []
        if entity_ids:
            events = await self._create_events(
                applet_id=applet_id,
                entity_ids=entity_ids,
                anchor_datetime=anchor_datetime,
            )
        return events

    def _generate_event_request(
        self,
        activity_id: uuid.UUID | None = None,
        flow_id: uuid.UUID | None = None,
    ):
        return EventRequest(
            timer=timedelta(minutes=1),
            timer_type=TimerType.NOT_SET,
            one_time_completion=self.random_boolean(),
            start_time="00:00",
            end_time="23:59",
            access_before_schedule=False,
            periodicity=PeriodicityRequest(
                type=PeriodicityType.ALWAYS,
                start_date=None,
                end_date=None,
                selected_date=None,
            ),
            respondent_id=None,
            activity_id=activity_id if activity_id else None,
            flow_id=flow_id if flow_id else None,
            notification={
                "notifications": [
                    NotificationSettingRequest(
                        trigger_type=NotificationTriggerType.FIXED,
                        at_time="08:00:00",
                    ),
                    NotificationSettingRequest(
                        trigger_type=NotificationTriggerType.RANDOM,
                        from_time="08:00:00",
                        to_time="09:00:00",
                    ),
                ],
                "reminder": ReminderSettingRequest(activity_incomplete=1, reminder_time="08:00:00"),
            },
        )

    def _get_generated_event(
        self,
        is_activity: bool,
        entity_id: uuid.UUID,
    ):
        if is_activity:
            default_event = self._generate_event_request(
                activity_id=entity_id,
            )
        else:
            default_event = self._generate_event_request(
                flow_id=entity_id,
            )
        return default_event

    async def _create_events(
        self,
        applet_id: uuid.UUID,
        anchor_datetime: datetime,
        entity_ids: list[dict] | None = None,
    ):
        events = []
        if entity_ids:
            # remove first entity id to keep it for default event
            entity_ids.pop(0)

            current_entity_index = 0
            # # first event always available and allow_access_before_schedule false # noqa: E501
            # default_event = self._get_generated_event(
            #     is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
            #         "is_activity"
            #     ),
            #     entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            # )
            # default_event.access_before_schedule = False
            # default_event = self._set_timer(
            #     default_event, current_entity_index
            # )

            # events.append(
            #     await ScheduleService(self.session).create_schedule(
            #         applet_id=applet_id,
            #         schedule=default_event,
            #     )
            # )
            # # second event always available and allow_access_before_schedule true # noqa: E501
            # current_entity_index = self._increment_index(
            #     current_entity_index, len(entity_ids)
            # )
            # default_event = self._get_generated_event(
            #     is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
            #         "is_activity"
            #     ),
            #     entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            # )
            # default_event.access_before_schedule = True
            # default_event = self._set_timer(
            #     default_event, current_entity_index
            # )
            # events.append(
            #     await ScheduleService(self.session).create_schedule(
            #         applet_id=applet_id,
            #         schedule=default_event,
            #     )
            # )

            # third event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )
            default_event.periodicity.start_date = anchor_datetime.date() - timedelta(days=5)
            default_event.periodicity.end_date = anchor_datetime.date() - timedelta(days=3)
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fourth event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )
            default_event.periodicity.start_date = anchor_datetime.date() - timedelta(days=2)
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=2)
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fifth event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )
            default_event.periodicity.start_date = anchor_datetime.date() + timedelta(days=2)
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=5)
            default_event.periodicity.type = PeriodicityType.DAILY
            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )
            # sixth event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.type = PeriodicityType.DAILY

            default_event.periodicity.start_date = anchor_datetime.date()
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=30)

            default_event.notification.notifications[0].at_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].from_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].to_time = (anchor_datetime + timedelta(minutes=120)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.reminder.reminder_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )

            default_event.start_time = (anchor_datetime + timedelta(minutes=60)).strftime("%H:%M:%S")
            default_event.end_time = (anchor_datetime + timedelta(minutes=180)).strftime("%H:%M:%S")
            default_event = self._set_timer(default_event, current_entity_index)

            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # seventh event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.type = PeriodicityType.DAILY

            default_event.periodicity.start_date = anchor_datetime.date()
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=30)

            default_event.notification.notifications[0].at_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].from_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].to_time = (anchor_datetime + timedelta(minutes=120)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.reminder.reminder_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )

            default_event.start_time = (anchor_datetime + timedelta(minutes=60)).strftime("%H:%M:%S")
            default_event.end_time = (anchor_datetime + timedelta(minutes=180)).strftime("%H:%M:%S")
            default_event.access_before_schedule = True

            default_event = self._set_timer(default_event, current_entity_index)

            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # eighth event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.type = PeriodicityType.DAILY

            default_event.periodicity.start_date = anchor_datetime.date()
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=30)

            default_event.notification.notifications[0].at_time = (anchor_datetime - timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].from_time = (anchor_datetime - timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].to_time = (anchor_datetime - timedelta(minutes=70)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.reminder.reminder_time = (anchor_datetime - timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )

            default_event.start_time = (anchor_datetime - timedelta(minutes=180)).strftime("%H:%M:%S")
            default_event.end_time = (anchor_datetime - timedelta(minutes=60)).strftime("%H:%M:%S")

            default_event = self._set_timer(default_event, current_entity_index)

            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # ninth event daily
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.type = PeriodicityType.DAILY

            default_event.periodicity.start_date = anchor_datetime.date()
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=30)

            default_event.notification.notifications[0].at_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].from_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.notifications[1].to_time = (anchor_datetime + timedelta(minutes=120)).strftime(
                "%H:%M:%S"
            )
            default_event.notification.reminder.reminder_time = (anchor_datetime + timedelta(minutes=90)).strftime(
                "%H:%M:%S"
            )

            default_event.start_time = (anchor_datetime - timedelta(minutes=180)).strftime("%H:%M:%S")
            default_event.end_time = (anchor_datetime + timedelta(minutes=180)).strftime("%H:%M:%S")

            default_event = self._set_timer(default_event, current_entity_index)

            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # tenth event weekly
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.selected_date = anchor_datetime.date() - timedelta(days=2)
            default_event.periodicity.type = PeriodicityType.WEEKLY

            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # eleventh event weekly
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.WEEKLY
            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # twelfth event weekly
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.selected_date = anchor_datetime.date() + timedelta(days=2)
            default_event.periodicity.type = PeriodicityType.WEEKLY
            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # thirteenth event montly
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.MONTHLY

            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fourteenth event weekdays
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.type = PeriodicityType.WEEKDAYS

            default_event.periodicity.start_date = anchor_datetime.date()
            default_event.periodicity.end_date = anchor_datetime.date() + timedelta(days=30)

            default_event = self._set_timer(default_event, current_entity_index)
            events.append(
                await ScheduleService(self.session).create_schedule(
                    applet_id=applet_id,
                    schedule=default_event,
                )
            )

            # fifteenth event once
            current_entity_index = self._increment_index(current_entity_index, len(entity_ids))
            default_event = self._get_generated_event(
                is_activity=entity_ids[current_entity_index].get(  # type: ignore  # noqa: E501
                    "is_activity"
                ),
                entity_id=entity_ids[current_entity_index].get("id"),  # type: ignore  # noqa: E501
            )

            default_event.periodicity.selected_date = anchor_datetime.date()
            default_event.periodicity.type = PeriodicityType.ONCE

            default_event = self._set_timer(default_event, current_entity_index)
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

    async def delete_generated_applets(self):
        # delete applets with suffix '-generated'

        old_applets = await AppletService(self.session, self.user_id).get_list_by_single_language(
            language="en",
            query_params=QueryParams(filters={"roles": Role.OWNER}),
        )

        if old_applets:
            for old_applet in old_applets:
                if old_applet.display_name.endswith("-generated"):
                    await AppletService(self.session, self.user_id).delete_applet_by_id(old_applet.id)
