from datetime import date, datetime, timedelta, time

from bson import ObjectId
from pydantic import BaseModel, Field

from apps.schedule.db.schemas import (
    PeriodicitySchema,
    EventSchema,
    UserEventsSchema,
    ActivityEventsSchema,
    FlowEventsSchema,
    NotificationSchema,
    ReminderSchema,
)
from apps.migrate.utilities import mongoid_to_uuid
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.crud.events import (
    EventCRUD,
    UserEventsCRUD,
    ActivityEventsCRUD,
    FlowEventsCRUD,
)
from apps.schedule.crud.notification import (
    NotificationCRUD,
    ReminderCRUD,
)
from apps.schedule.domain.constants import PeriodicityType
from apps.girderformindlogger.models.profile import Profile

from infrastructure.database import atomic


__all__ = [
    "MongoEvent",
    "EventMigrationService",
]


DEFAULT_PERIODICITY_TYPE: str = "ALWAYS"
NOT_SET: str = "NOT_SET"
TIMER: str = "TIMER"
IDLE: str = "IDLE"
TIMER_TYPE: dict = {
    NOT_SET: NOT_SET,
    TIMER: TIMER,
    IDLE: IDLE,
}


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ExtendedTime(BaseModel):
    allow: bool
    days: int | None
    minute: int | None


class IdleTime(BaseModel):
    allow: bool
    minute: int | str


class Notifications(BaseModel):
    allow: bool | None
    end: str | None
    notifyIfIncomplete: bool | None
    random: bool
    start: str | None


class Reminder(BaseModel):
    days: int | str
    time: str
    valid: bool


class TimedActivity(BaseModel):
    allow: bool
    hour: int
    minute: int
    second: int


class Timeout(BaseModel):
    access: bool
    allow: bool
    day: int
    hour: int
    minute: int


class Data(BaseModel):
    activity_flow_id: PyObjectId | None
    activity_id: PyObjectId | None
    availability: bool | None
    busy: bool
    calendar: str
    color: str
    completion: bool | None
    description: str
    eventType: str | None
    extendedTime: ExtendedTime | None
    forecolor: str
    icon: str
    idleTime: IdleTime | None
    isActivityFlow: bool | None
    location: str
    notifications: list[Notifications] | None
    onlyScheduledDay: bool | None
    reminder: Reminder | None
    timedActivity: TimedActivity | None
    timeout: Timeout
    title: str
    URI: str | None
    useNotifications: bool | None
    users: list[PyObjectId] | None


class Schedule(BaseModel):
    dayOfMonth: list[int] | None
    dayOfWeek: list[int | list[int]] | None
    duration: int | None
    durationUnit: str | None
    end: int | None
    include: list[int] | None
    month: list[int] | None
    start: int | None
    times: list[str] | None
    year: list[int] | None


class MongoEvent(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    applet_id: PyObjectId = Field(default_factory=PyObjectId)
    data: Data
    individualized: bool
    schedule: Schedule
    schedulers: list[str]
    sendTime: list[str]
    updated: date | None


class EventMigrationService:
    def __init__(self, session, events: list[MongoEvent]):
        self.session = session
        self.events = events

    async def _create_periodicity(
        self, event: MongoEvent
    ) -> PeriodicitySchema:
        periodicity_data: dict = {}

        if event.data.eventType is None:
            periodicity_data["type"] = PeriodicityType.ALWAYS
        elif isinstance(event.data.eventType, str):
            periodicity_data["type"] = event.data.eventType.upper()
            if event.data.eventType == "":
                periodicity_data["type"] = PeriodicityType.ONCE

            if periodicity_data["type"] in (
                PeriodicityType.ONCE,
                PeriodicityType.WEEKLY,
                PeriodicityType.MONTHLY,
            ):
                if (
                    event.schedule.dayOfMonth
                    and event.schedule.month
                    and event.schedule.year
                ):
                    try:
                        periodicity_data["selected_date"] = date(
                            event.schedule.year[0],
                            event.schedule.month[0] + 1,
                            event.schedule.dayOfMonth[0],
                        )
                    except ValueError:
                        periodicity_data["selected_date"] = self._find_date(
                            event
                        )
                else:
                    periodicity_data["selected_date"] = self._find_date(event)

                if (
                    event.schedule.dayOfWeek
                    and len(event.schedule.dayOfWeek) > 1
                ):
                    periodicity_data["type"] = PeriodicityType.WEEKDAYS

        if event.schedule.start:
            periodicity_data["start_date"] = datetime.utcfromtimestamp(
                event.schedule.start / 1000
            )
        if event.schedule.end:
            periodicity_data["end_date"] = datetime.utcfromtimestamp(
                event.schedule.end / 1000
            )

        periodicity_data["migrated_date"] = datetime.utcnow()
        periodicity_data["migrated_updated"] = datetime.utcnow()
        periodicity = PeriodicitySchema(**periodicity_data)

        async with atomic(self.session):
            await PeriodicityCRUD(self.session)._create(periodicity)

        return periodicity

    async def _create_event(
        self, event: MongoEvent, periodicity: PeriodicitySchema
    ) -> EventSchema:
        event_data: dict = {}

        times = event.schedule.times[0] if event.schedule.times else "00:00"
        start_time, end_time = self._calculate_time(
            times,
            {
                "hour": event.data.timeout.hour,
                "minute": event.data.timeout.minute,
            },
        )
        event_data["start_time"] = start_time
        event_data["end_time"] = end_time

        if event.data.onlyScheduledDay is None:
            event_data["access_before_schedule"] = None
        elif event.data.onlyScheduledDay:
            event_data["access_before_schedule"] = True
        else:
            event_data["access_before_schedule"] = False

        if periodicity.type is None:
            event_data["one_time_completion"] = None
        elif periodicity.type == PeriodicityType.ONCE:
            event_data["one_time_completion"] = True
        else:
            event_data["one_time_completion"] = False

        if event.data.idleTime:
            event_data["timer_type"] = TIMER_TYPE[IDLE]
            event_data["timer"] = timedelta(
                minutes=float(event.data.idleTime.minute)
            )
        else:
            event_data["timer_type"] = TIMER_TYPE[NOT_SET]

        event_data["applet_id"] = mongoid_to_uuid(event.applet_id)

        event_data["periodicity_id"] = periodicity.id

        event_data["migrated_date"] = datetime.utcnow()

        pg_event = EventSchema(**event_data)

        async with atomic(self.session):
            await EventCRUD(self.session)._create(pg_event)

        return pg_event

    async def _create_user(self, event: MongoEvent, pg_event: EventSchema):
        if event.data.users and event.data.users[0]:
            user = event.data.users[0]
        else:
            raise Exception("No user for individual event")
        profile = Profile().findOne(query={"_id": ObjectId(user)})
        if not profile:
            raise Exception("Unable to find profile by event")
        user = profile["userId"]
        user_event_data = {
            "user_id": mongoid_to_uuid(user),
            "event_id": pg_event.id,
        }
        user_event_data["migrated_date"] = datetime.utcnow()
        user_event_data["migrated_updated"] = datetime.utcnow()
        user_event = UserEventsSchema(**user_event_data)

        async with atomic(self.session):
            await UserEventsCRUD(self.session)._create(user_event)

    async def _create_activity(self, event: MongoEvent, pg_event: EventSchema):
        now = datetime.utcnow()
        activity_event_data: dict = {
            "activity_id": mongoid_to_uuid(event.data.activity_id),
            "event_id": pg_event.id,
        }
        activity_event_data["migrated_date"] = datetime.utcnow()
        activity_event_data["migrated_updated"] = datetime.utcnow()
        activity = ActivityEventsSchema(**activity_event_data)

        async with atomic(self.session):
            await ActivityEventsCRUD(self.session)._create(activity)

    async def _create_flow(self, event: MongoEvent, pg_event: EventSchema):
        flow_event_data: dict = {
            "flow_id": mongoid_to_uuid(event.data.activity_flow_id),
            "event_id": pg_event.id,
        }
        flow_event_data["migrated_date"] = datetime.utcnow()
        flow_event_data["migrated_updated"] = datetime.utcnow()
        flow = FlowEventsSchema(**flow_event_data)

        async with atomic(self.session):
            await FlowEventsCRUD(self.session)._create(flow)

    async def _create_notification(
        self, event: MongoEvent, pg_event: EventSchema
    ):
        notifications: list = []
        order: int = 1
        if event.data.notifications:
            for notification in event.data.notifications:
                if notification.allow:
                    notification_data: dict = {}
                    if notification.random:
                        if notification.start and notification.end:
                            notification_data["trigger_type"] = "RANDOM"

                            notification_data["from_time"] = datetime.strptime(
                                notification.start, "%H:%M"
                            ).time()

                            notification_data["to_time"] = datetime.strptime(
                                notification.end, "%H:%M"
                            ).time()
                        else:
                            continue
                    else:
                        if notification.start:
                            notification_data["trigger_type"] = "FIXED"
                            notification_data["at_time"] = datetime.strptime(
                                notification.start, "%H:%M"
                            ).time()
                        else:
                            continue
                    notification_data["event_id"] = pg_event.id
                    notification_data["migrated_date"] = datetime.utcnow()
                    notification_data["migrated_updated"] = datetime.utcnow()
                    notification_data["order"] = order
                    order += 1

                    notifications.append(
                        NotificationSchema(**notification_data)
                    )

        async with atomic(self.session):
            await NotificationCRUD(self.session).create_many(notifications)

    async def _create_reminder(self, event: MongoEvent, pg_event: EventSchema):
        if event.data.reminder:
            reminder_data: dict = {
                "event_id": pg_event.id,
                "activity_incomplete": int(event.data.reminder.days),
                "reminder_time": datetime.strptime(
                    event.data.reminder.time, "%H:%M"
                ).time(),
            }
            reminder_data["migrated_date"] = datetime.utcnow()
            reminder_data["migrated_updated"] = datetime.utcnow()
            reminder = ReminderSchema(**reminder_data)

            async with atomic(self.session):
                await ReminderCRUD(self.session)._create(reminder)

    async def run_events_migration(self):
        number_of_errors: int = 0
        number_of_events_in_mongo: int = len(self.events)
        for i, event in enumerate(self.events, 1):
            print(
                f"Migrate events {i}/{number_of_events_in_mongo}. Working on Event: {event.id}"
            )
            try:
                # Migrate data to PeriodicitySchema
                periodicity = await self._create_periodicity(event)

                # Migrate data to EventSchema
                pg_event = await self._create_event(event, periodicity)

                # Migrate data to UserEventsSchema (if individualized)
                if event.individualized:
                    await self._create_user(event, pg_event)

                # Migrate data to ActivityEventsSchema or FlowEventsSchema
                if event.data.activity_id:
                    await self._create_activity(event, pg_event)
                if event.data.activity_flow_id:
                    await self._create_flow(event, pg_event)

                # Migrate data to NotificationSchema
                if event.data.notifications:
                    await self._create_notification(event, pg_event)

                # Migrate data to ReminderSchema
                if (
                    event.data.reminder
                    and event.data.reminder.valid
                    and event.data.reminder.time
                ):
                    await self._create_reminder(event, pg_event)
            except Exception as e:
                number_of_errors += 1
                print(f"Skipped Event: {event.id}", str(e))
                continue

        print(f"Number of skiped events: {number_of_errors}")

    def _find_date(self, event: MongoEvent):
        if event.data.eventType.upper() == PeriodicityType.WEEKLY:
            return self._find_closest_date_by_week_day(
                event.schedule.dayOfWeek[0]
            )
        if event.data.eventType.upper() == PeriodicityType.MONTHLY:
            return self._find_closest_date_by_month_day(
                event.schedule.dayOfMonth[0]
            )

    def _find_closest_date_by_week_day(self, target_day_of_week):
        today = date.today()

        if isinstance(target_day_of_week, list):
            return today

        days_until_target = target_day_of_week - today.isoweekday()

        if days_until_target <= 0:
            days_until_target += 7  # If the target day has already passed this week, move to the next week

        closest_date = today + timedelta(days=days_until_target)

        return closest_date

    def _find_closest_date_by_month_day(self, target_day_of_month: int):
        today = date.today()

        current_month = today.month
        current_year = today.year

        try:
            target_date = date(
                current_year, current_month, target_day_of_month
            )
        except ValueError:
            target_date = date(
                current_year, current_month + 1, target_day_of_month
            )

        days_until_target = (target_date - today).days

        if days_until_target < 0:
            next_month = current_month + 1
            if next_month > 12:
                next_month = 1
                current_year += 1
            target_date = date(current_year, next_month, target_day_of_month)
            days_until_target = (target_date - today).days

        return target_date

    def _calculate_time(self, input_time: str, time_dict: dict):
        try:
            if ":" in input_time:
                input_hour, input_minute = map(int, input_time.split(":"))
            else:
                input_hour = int(input_time)
                input_minute = 0

            hour_delta = time_dict.get("hour", 0)
            minute_delta = time_dict.get("minute", 0)

            new_hour = input_hour + hour_delta
            new_minute = input_minute + minute_delta

            if new_hour >= 24:
                new_hour = 23
                new_minute = 59

            new_hour = max(0, min(23, new_hour))
            new_minute = max(0, min(59, new_minute))

            original_time = time(input_hour, input_minute)
            modified_time = time(new_hour, new_minute)

            return original_time, modified_time
        except ValueError:
            raise Exception("Unable to parse start or end tiem")
