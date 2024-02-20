import asyncio
import uuid
from datetime import date

from apps.activities.crud import ActivitiesCRUD
from apps.activity_flows.crud import FlowsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.errors import AppletNotFoundError
from apps.schedule.crud.events import ActivityEventsCRUD, EventCRUD, FlowEventsCRUD, UserEventsCRUD
from apps.schedule.crud.notification import NotificationCRUD, ReminderCRUD
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.db.schemas import EventSchema, NotificationSchema
from apps.schedule.domain.constants import AvailabilityType, DefaultEvent, PeriodicityType, TimerType
from apps.schedule.domain.schedule import BaseEvent
from apps.schedule.domain.schedule.internal import (
    ActivityEventCreate,
    Event,
    EventCreate,
    EventFull,
    EventUpdate,
    FlowEventCreate,
    NotificationSetting,
    Periodicity,
    ReminderSetting,
    ReminderSettingCreate,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import (
    EventAvailabilityDto,
    HourMinute,
    NotificationDTO,
    NotificationSettingDTO,
    PublicEvent,
    PublicEventByUser,
    PublicEventCount,
    PublicNotification,
    PublicNotificationSetting,
    PublicPeriodicity,
    PublicReminderSetting,
    ReminderSettingDTO,
    ScheduleEventDto,
    TimerDto,
)
from apps.schedule.domain.schedule.requests import EventRequest, EventUpdateRequest
from apps.schedule.errors import (
    AccessDeniedToApplet,
    ActivityOrFlowNotFoundError,
    AppletScheduleNotFoundError,
    EventAlwaysAvailableExistsError,
    ScheduleNotFoundError,
)
from apps.shared.query_params import QueryParams
from apps.users.cruds.user import UsersCRUD
from apps.users.errors import UserNotFound
from apps.workspaces.domain.constants import Role

__all__ = ["ScheduleService"]


class ScheduleService:
    def __init__(self, session):
        self.session = session

    async def create_schedule(self, schedule: EventRequest, applet_id: uuid.UUID) -> PublicEvent:
        # Validate schedule data before saving
        await self._validate_schedule(applet_id=applet_id, schedule=schedule)

        # Delete all events of this activity or flow
        # if new periodicity type is "always"

        if schedule.periodicity.type == PeriodicityType.ALWAYS:
            # check if there is any AlwaysAvailable event, if yes, raise error
            await self._validate_existing_alwaysavailable(
                applet_id=applet_id,
                activity_id=schedule.activity_id,
                flow_id=schedule.flow_id,
                respondent_id=schedule.respondent_id,
            )

        # delete alwaysAvailable events of this activity or flow,
        # if new event type is not AA
        # else, delete all types
        await self._delete_by_activity_or_flow(
            applet_id=applet_id,
            activity_id=schedule.activity_id,
            flow_id=schedule.flow_id,
            respondent_id=schedule.respondent_id,
            only_always_available=(schedule.periodicity.type != PeriodicityType.ALWAYS),
        )

        # Create periodicity
        periodicity: Periodicity = await PeriodicityCRUD(self.session).save(schedule.periodicity)

        # Create event
        event: Event = await EventCRUD(self.session).save(
            EventCreate(
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                access_before_schedule=schedule.access_before_schedule,
                one_time_completion=schedule.one_time_completion,
                timer=schedule.timer,
                timer_type=schedule.timer_type,
                periodicity_id=periodicity.id,
                applet_id=applet_id,
            )
        )

        # Create event-user
        if schedule.respondent_id:
            await UserEventsCRUD(self.session).save(UserEventCreate(event_id=event.id, user_id=schedule.respondent_id))
        # Create event-activity or event-flow
        if schedule.activity_id:
            await ActivityEventsCRUD(self.session).save(
                ActivityEventCreate(event_id=event.id, activity_id=schedule.activity_id)
            )
        else:
            await FlowEventsCRUD(self.session).save(FlowEventCreate(event_id=event.id, flow_id=schedule.flow_id))

        # Create notification and reminder
        if schedule.notification:
            notifications = None
            reminder = None

            if schedule.notification.notifications:
                notification_create = []
                for notification in schedule.notification.notifications:
                    notification_create.append(
                        NotificationSchema(
                            event_id=event.id,
                            from_time=notification.from_time,
                            to_time=notification.to_time,
                            at_time=notification.at_time,
                            trigger_type=notification.trigger_type,
                            order=notification.order,
                        )
                    )
                notifications = await NotificationCRUD(self.session).create_many(notification_create)

            if schedule.notification.reminder:
                reminder = await ReminderCRUD(self.session).create(
                    ReminderSettingCreate(
                        event_id=event.id,
                        activity_incomplete=schedule.notification.reminder.activity_incomplete,  # noqa: E501
                        reminder_time=schedule.notification.reminder.reminder_time,  # noqa: E501
                    )
                )
            notification_public = PublicNotification(
                notifications=[
                    PublicNotificationSetting(
                        **notification.dict(),
                    )
                    for notification in notifications
                ]
                if notifications
                else None,
                reminder=PublicReminderSetting(
                    **reminder.dict(),
                )
                if reminder
                else None,
            )

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            respondent_id=schedule.respondent_id,
            activity_id=schedule.activity_id,
            flow_id=schedule.flow_id,
            notification=notification_public if schedule.notification else None,
        )

    async def get_schedule_by_id(self, schedule_id: uuid.UUID, applet_id: uuid.UUID) -> PublicEvent:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event: Event = await EventCRUD(self.session).get_by_id(pk=schedule_id)
        periodicity: Periodicity = await PeriodicityCRUD(self.session).get_by_id(event.periodicity_id)
        user_id = await UserEventsCRUD(self.session).get_by_event_id(event_id=event.id)
        activity_id = await ActivityEventsCRUD(self.session).get_by_event_id(event_id=event.id)
        flow_id = await FlowEventsCRUD(self.session).get_by_event_id(event_id=event.id)
        notification = await self._get_notifications_and_reminder(event.id)

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            respondent_id=user_id,
            activity_id=activity_id,
            flow_id=flow_id,
            notification=notification,
        )

    async def get_all_schedules(self, applet_id: uuid.UUID, query: QueryParams) -> list[PublicEvent]:
        # validate respondent_id if present
        if "respondent_id" in query.filters:
            respondent_id = query.filters["respondent_id"]
            await self._validate_user(respondent_id)
        else:
            respondent_id = None

        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event_schemas: list[EventSchema] = await EventCRUD(self.session).get_all_by_applet_id_with_filter(
            applet_id, respondent_id
        )
        events: list[PublicEvent] = []

        for event_schema in event_schemas:
            event: Event = Event.from_orm(event_schema)

            periodicity: Periodicity = await PeriodicityCRUD(self.session).get_by_id(event.periodicity_id)
            user_id = await UserEventsCRUD(self.session).get_by_event_id(event_id=event.id)
            activity_id = await ActivityEventsCRUD(self.session).get_by_event_id(event_id=event.id)
            flow_id = await FlowEventsCRUD(self.session).get_by_event_id(event_id=event.id)
            notification = await self._get_notifications_and_reminder(event.id)

            events.append(
                PublicEvent(
                    **event.dict(),
                    periodicity=PublicPeriodicity(**periodicity.dict()),
                    respondent_id=user_id,
                    activity_id=activity_id,
                    flow_id=flow_id,
                    notification=notification,
                )
            )

        return events

    async def get_public_all_schedules(self, key: uuid.UUID) -> PublicEventByUser:
        # Check if applet exists by link key
        applet_id = await self._validate_public_applet(key)

        event_schemas: list[EventSchema] = await EventCRUD(self.session).get_public_by_applet_id(applet_id)

        full_events: list[EventFull] = []
        for event_schema in event_schemas:
            event: Event = Event.from_orm(event_schema)
            periodicity: Periodicity = await PeriodicityCRUD(self.session).get_by_id(event.periodicity_id)
            activity_id = await ActivityEventsCRUD(self.session).get_by_event_id(event_id=event.id)
            flow_id = await FlowEventsCRUD(self.session).get_by_event_id(event_id=event.id)
            base_event = BaseEvent(**event.dict())

            full_events.append(
                EventFull(
                    id=event.id,
                    **base_event.dict(),
                    periodicity=periodicity,
                    activity_id=activity_id,
                    flow_id=flow_id,
                )
            )

        events = PublicEventByUser(
            applet_id=applet_id,
            events=[
                self._convert_to_dto(
                    event=full_event,
                    notifications=await NotificationCRUD(self.session).get_all_by_event_id(full_event.id),
                    reminder=await ReminderCRUD(self.session).get_by_event_id(full_event.id),
                )
                for full_event in full_events
            ],
        )

        return events

    async def delete_all_schedules(self, applet_id: uuid.UUID):
        """Delete all default events"""

        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event_schemas: list[EventSchema] = await EventCRUD(self.session).get_all_by_applet_id_with_filter(applet_id)
        event_ids = [event_schema.id for event_schema in event_schemas]
        periodicity_ids = [event_schema.periodicity_id for event_schema in event_schemas]
        if not event_ids:
            raise AppletScheduleNotFoundError(applet_id=applet_id)

        # Get all activity_ids and flow_ids
        activity_ids = await ActivityEventsCRUD(self.session).get_by_event_ids(event_ids)
        flow_ids = await FlowEventsCRUD(self.session).get_by_event_ids(event_ids)

        await self._delete_by_ids(event_ids, periodicity_ids)

        # Create default events for activities and flows
        for activity_id in activity_ids:
            await self._create_default_event(applet_id=applet_id, activity_id=activity_id, is_activity=True)

        for flow_id in flow_ids:
            await self._create_default_event(applet_id=applet_id, activity_id=flow_id, is_activity=False)

    async def delete_schedule_by_id(self, schedule_id: uuid.UUID, applet_id: uuid.UUID) -> uuid.UUID | None:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event: Event = await EventCRUD(self.session).get_by_id(pk=schedule_id)
        periodicity_id = event.periodicity_id
        respondent_id = await UserEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)

        # Get activity_id or flow_id if exists
        activity_id = await ActivityEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)
        flow_id = await FlowEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)

        # Delete event-user, event-activity, event-flow
        await self._delete_by_ids(event_ids=[schedule_id], periodicity_ids=[periodicity_id])
        # Create default event for activity or flow if another event doesn't exist # noqa: E501
        if activity_id:
            count_events = await ActivityEventsCRUD(self.session).count_by_activity(
                activity_id=activity_id, respondent_id=respondent_id
            )
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=activity_id,
                    is_activity=True,
                    respondent_id=respondent_id,
                )

        elif flow_id:
            count_events = await FlowEventsCRUD(self.session).count_by_flow(
                flow_id=flow_id, respondent_id=respondent_id
            )
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=flow_id,
                    is_activity=False,
                    respondent_id=respondent_id,
                )
        return respondent_id

    async def update_schedule(
        self,
        applet_id: uuid.UUID,
        schedule_id: uuid.UUID,
        schedule: EventUpdateRequest,
    ) -> PublicEvent:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event: Event = await EventCRUD(self.session).get_by_id(pk=schedule_id)
        activity_id = await ActivityEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)
        flow_id = await FlowEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)
        respondent_id = await UserEventsCRUD(self.session).get_by_event_id(event_id=schedule_id)
        periodicity: Periodicity = await PeriodicityCRUD(self.session).get_by_id(event.periodicity_id)

        # Delete all events of this activity or flow
        # if new periodicity type is "always" and old periodicity type is not "always" # noqa: E501
        if schedule.periodicity.type == PeriodicityType.ALWAYS and periodicity.type != PeriodicityType.ALWAYS:  # noqa: E501
            await self._delete_by_activity_or_flow(
                applet_id=applet_id,
                activity_id=activity_id,
                flow_id=flow_id,
                respondent_id=respondent_id,
                only_always_available=False,
                except_event_id=schedule_id,
            )

        # Update periodicity
        periodicity = await PeriodicityCRUD(self.session).update(pk=periodicity.id, schema=schedule.periodicity)

        # Update event
        event = await EventCRUD(self.session).update(
            pk=schedule_id,
            schema=EventUpdate(
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                access_before_schedule=schedule.access_before_schedule,
                one_time_completion=schedule.one_time_completion,
                timer=schedule.timer,
                timer_type=schedule.timer_type,
                periodicity_id=periodicity.id,
                applet_id=applet_id,
            ),
        )
        # Update notification
        await NotificationCRUD(self.session).delete_by_event_ids([schedule_id])
        await ReminderCRUD(self.session).delete_by_event_ids([schedule_id])

        notification_public = None
        if schedule.notification:
            notifications = None
            reminder = None
            if schedule.notification.notifications:
                notifications_create = []
                for notification in schedule.notification.notifications:
                    notifications_create.append(
                        NotificationSchema(
                            event_id=event.id,
                            from_time=notification.from_time,
                            to_time=notification.to_time,
                            at_time=notification.at_time,
                            trigger_type=notification.trigger_type,
                            order=notification.order,
                        )
                    )
                notifications = await NotificationCRUD(self.session).create_many(notifications_create)

            if schedule.notification.reminder:
                reminder = await ReminderCRUD(self.session).create(
                    reminder=ReminderSettingCreate(
                        event_id=event.id,
                        activity_incomplete=schedule.notification.reminder.activity_incomplete,  # noqa: E501
                        reminder_time=schedule.notification.reminder.reminder_time,  # noqa: E501
                    )
                )
            notification_public = PublicNotification(
                notifications=[
                    PublicNotificationSetting(
                        **notification.dict(),
                    )
                    for notification in notifications
                ]
                if notifications
                else None,
                reminder=PublicReminderSetting(
                    **reminder.dict(),
                )
                if reminder
                else None,
            )

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            respondent_id=respondent_id,
            activity_id=activity_id,
            flow_id=flow_id,
            notification=notification_public,
        )

    async def _validate_schedule(self, applet_id: uuid.UUID, schedule: EventRequest) -> None:
        """Validate schedule before saving it to the database."""
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        # Check if user has access to applet
        if schedule.respondent_id:
            user_applet_access = await UserAppletAccessCRUD(self.session).get_by_applet_and_user_as_respondent(
                applet_id=applet_id, user_id=schedule.respondent_id
            )  # noqa: E501
            if not user_applet_access:
                raise AccessDeniedToApplet()

        # Check if activity or flow exists inside applet
        activity_or_flow = None
        if schedule.activity_id:
            activity_or_flow = await ActivitiesCRUD(self.session).get_by_applet_id_and_activity_id(
                applet_id=applet_id, activity_id=schedule.activity_id
            )
        if schedule.flow_id:
            activity_or_flow = await FlowsCRUD(self.session).get_by_applet_id_and_flow_id(
                applet_id=applet_id, flow_id=schedule.flow_id
            )
        if not activity_or_flow:
            raise ActivityOrFlowNotFoundError()

    async def count_schedules(self, applet_id: uuid.UUID) -> PublicEventCount:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event_count = PublicEventCount(activity_events=[], flow_events=[])

        # Get list of activity-event ids
        activity_counts = await ActivityEventsCRUD(self.session).count_by_applet(applet_id=applet_id)

        # Get list of flow-event ids
        flow_counts = await FlowEventsCRUD(self.session).count_by_applet(applet_id=applet_id)

        event_count.activity_events = activity_counts if activity_counts else []
        event_count.flow_events = flow_counts if flow_counts else []

        return event_count

    async def delete_by_user_id(self, applet_id, user_id):
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        # Check if user exists
        await self._validate_user(user_id=user_id)

        # Get list of activity-event ids and flow-event ids for user to create default events  # noqa: E501
        activities = await ActivityEventsCRUD(self.session).get_by_applet_and_user_id(applet_id, user_id)

        activity_ids = {activity.activity_id for activity in activities}

        flows = await FlowEventsCRUD(self.session).get_by_applet_and_user_id(applet_id, user_id)
        flow_ids = {flow.flow_id for flow in flows}

        # Get list of event_ids for user and delete them all
        event_schemas = await EventCRUD(self.session).get_all_by_applet_and_user(applet_id, user_id)
        event_ids = [event_schema.id for event_schema in event_schemas]
        periodicity_ids = [event_schema.periodicity.id for event_schema in event_schemas]
        if not event_ids:
            raise ScheduleNotFoundError()
        await self._delete_by_ids(
            event_ids,
            periodicity_ids,
            user_id,
        )
        # Create AA events for all activities and flows
        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=list(activity_ids),
            is_activity=True,
            respondent_id=user_id,
        )
        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=list(flow_ids),
            is_activity=False,
            respondent_id=user_id,
        )

    async def _create_default_event(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        is_activity: bool,
        respondent_id: uuid.UUID | None = None,
    ) -> None:
        """Create default schedules for applet."""
        default_event = DefaultEvent()
        if is_activity:
            default_event.activity_id = activity_id
        else:
            default_event.flow_id = activity_id

        default_event.respondent_id = respondent_id

        # Create default event
        await self.create_schedule(applet_id=applet_id, schedule=EventRequest(**default_event.dict()))

    async def _delete_by_activity_or_flow(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID | None,
        flow_id: uuid.UUID | None,
        respondent_id: uuid.UUID | None = None,
        only_always_available: bool = False,
        except_event_id: uuid.UUID | None = None,
    ) -> None:
        """Delete schedules by activity or flow id."""
        event_schemas = []

        if activity_id:
            # Get list of event_ids for activity and delete them all
            event_schemas = await EventCRUD(self.session).get_all_by_applet_and_activity(
                applet_id,
                activity_id,
                respondent_id,
                only_always_available,
            )
        elif flow_id:
            # Get list of event_ids for flow and delete them all
            event_schemas = await EventCRUD(self.session).get_all_by_applet_and_flow(
                applet_id,
                flow_id,
                respondent_id,
                only_always_available,
            )

        clean_events = [event for event in event_schemas if event.id != except_event_id]
        event_ids = [event.id for event in clean_events]
        periodicity_ids = [event.periodicity_id for event in clean_events]

        if event_ids:
            await self._delete_by_ids(event_ids=event_ids, periodicity_ids=periodicity_ids)

    async def _delete_by_ids(
        self,
        event_ids: list[uuid.UUID],
        periodicity_ids: list[uuid.UUID],
        user_id: uuid.UUID | None = None,
    ):
        if user_id:
            await UserEventsCRUD(self.session).delete_all_by_events_and_user(
                event_ids,
                user_id,
            )
        else:
            await UserEventsCRUD(self.session).delete_all_by_event_ids(event_ids)

        await ActivityEventsCRUD(self.session).delete_all_by_event_ids(event_ids)
        await FlowEventsCRUD(self.session).delete_all_by_event_ids(event_ids)
        await NotificationCRUD(self.session).delete_by_event_ids(event_ids)
        await ReminderCRUD(self.session).delete_by_event_ids(event_ids)
        await EventCRUD(self.session).delete_by_ids(event_ids)
        await PeriodicityCRUD(self.session).delete_by_ids(periodicity_ids)

    async def delete_by_activity_ids(self, applet_id: uuid.UUID, activity_ids: list[uuid.UUID]) -> None:
        """Delete schedules by activity ids."""
        events = await EventCRUD(self.session).get_all_by_activity_flow_ids(applet_id, activity_ids, True)
        event_ids = [event.id for event in events]
        periodicity_ids = [event.periodicity_id for event in events]
        await self._delete_by_ids(event_ids, periodicity_ids)

    async def delete_by_flow_ids(self, applet_id: uuid.UUID, flow_ids: list[uuid.UUID]) -> None:
        """Delete schedules by flow ids."""
        events = await EventCRUD(self.session).get_all_by_activity_flow_ids(applet_id, flow_ids, False)
        event_ids = [event.id for event in events]
        periodicity_ids = [event.periodicity_id for event in events]
        await self._delete_by_ids(event_ids, periodicity_ids)

    async def create_default_schedules(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID],
        is_activity: bool,
        respondent_id: uuid.UUID | None = None,
    ) -> None:
        """Create default schedules for applet."""
        for activity_id in activity_ids:
            await self._create_default_event(
                applet_id=applet_id,
                activity_id=activity_id,
                is_activity=is_activity,
                respondent_id=respondent_id,
            )

    async def get_events_by_user(self, user_id: uuid.UUID) -> list[PublicEventByUser]:
        """Get all events for user in applets that user is respondent."""
        applets = await AppletsCRUD(self.session).get_applets_by_roles(
            user_id=user_id,
            roles=Role.as_list(),
            query_params=QueryParams(),
        )
        applet_ids = [applet.id for applet in applets]
        events = []

        for applet_id in applet_ids:
            user_events: list = await EventCRUD(self.session).get_all_by_applet_and_user(
                applet_id=applet_id,
                user_id=user_id,
            )
            general_events: list = await EventCRUD(self.session).get_general_events_by_user(
                applet_id=applet_id, user_id=user_id
            )
            all_events = user_events + general_events
            events.append(
                PublicEventByUser(
                    applet_id=applet_id,
                    events=[
                        self._convert_to_dto(
                            event=event,
                            notifications=await NotificationCRUD(self.session).get_all_by_event_id(event.id),
                            reminder=await ReminderCRUD(self.session).get_by_event_id(event.id),
                        )
                        for event in all_events
                    ],
                )
            )

        return events

    async def get_upcoming_events_by_user(
        self,
        user_id: uuid.UUID,
        applet_ids: list[uuid.UUID],
        min_end_date: date | None = None,
        max_start_date: date | None = None,
    ) -> list[PublicEventByUser]:
        """Get all events for user in applets that user is respondent."""
        user_events_map, user_event_ids = await EventCRUD(self.session).get_all_by_applets_and_user(
            applet_ids=applet_ids,
            user_id=user_id,
            min_end_date=min_end_date,
            max_start_date=max_start_date,
        )
        general_events_map, general_event_ids = await EventCRUD(self.session).get_general_events_by_applets_and_user(
            applet_ids=applet_ids,
            user_id=user_id,
            min_end_date=min_end_date,
            max_start_date=max_start_date,
        )
        full_events_map = self._sum_applets_events_map(user_events_map, general_events_map)

        event_ids = user_event_ids | general_event_ids
        notifications_map_c = NotificationCRUD(self.session).get_all_by_event_ids(event_ids)
        reminders_map_c = ReminderCRUD(self.session).get_by_event_ids(event_ids)
        notifications_map, reminders_map = await asyncio.gather(notifications_map_c, reminders_map_c)

        events: list[PublicEventByUser] = []
        for applet_id, all_events in full_events_map.items():
            events.append(
                PublicEventByUser(
                    applet_id=applet_id,
                    events=[
                        self._convert_to_dto(
                            event=event,
                            notifications=notifications_map.get(event.id),
                            reminder=reminders_map.get(event.id),
                        )
                        for event in all_events
                    ],
                )
            )

        return events

    @staticmethod
    def _sum_applets_events_map(m1: dict, m2: dict):
        result = dict()
        for k, v in m1.items():
            result[k] = v
        for k, v in m2.items():
            result.setdefault(k, list())
            result[k] += v
        return result

    def _convert_to_dto(
        self,
        event: EventFull,
        notifications: list[NotificationSetting] | None = None,
        reminder: ReminderSetting | None = None,
    ) -> ScheduleEventDto:
        """Convert event to dto."""
        timers = TimerDto(
            timer=HourMinute(
                hours=event.timer.seconds // 3600 if event.timer else 0,
                minutes=event.timer.seconds // 60 % 60 if event.timer else 0,
            )
            if event.timer_type == TimerType.TIMER
            else None,
            idleTimer=HourMinute(
                hours=event.timer.seconds // 3600 if event.timer else 0,
                minutes=event.timer.seconds // 60 % 60 if event.timer else 0,
            )
            if event.timer_type == TimerType.IDLE
            else None,
        )

        availabilityType = (
            AvailabilityType.ALWAYS_AVAILABLE
            if event.periodicity.type == PeriodicityType.ALWAYS
            else AvailabilityType.SCHEDULED_ACCESS
        )

        availability = EventAvailabilityDto(
            oneTimeCompletion=event.one_time_completion,
            periodicityType=event.periodicity.type,
            timeFrom=HourMinute(
                hours=event.start_time.hour if event.start_time else 0,
                minutes=event.start_time.minute if event.start_time else 0,
            ),
            timeTo=HourMinute(
                hours=event.end_time.hour if event.end_time else 0,
                minutes=event.end_time.minute if event.end_time else 0,
            ),
            allowAccessBeforeFromTime=event.access_before_schedule,
            startDate=event.periodicity.start_date,
            endDate=event.periodicity.end_date,
        )

        notificationSettings = None
        if notifications or reminder:
            notificationsDTO = None
            reminderDTO = None
            if notifications:
                notificationsDTO = [
                    NotificationSettingDTO(
                        trigger_type=notification.trigger_type,
                        from_time=HourMinute(
                            hours=notification.from_time.hour,
                            minutes=notification.from_time.minute,
                        )
                        if notification.from_time
                        else None,
                        to_time=HourMinute(
                            hours=notification.to_time.hour,
                            minutes=notification.to_time.minute,
                        )
                        if notification.to_time
                        else None,
                        at_time=HourMinute(
                            hours=notification.at_time.hour,
                            minutes=notification.at_time.minute,
                        )
                        if notification.at_time
                        else None,
                    )
                    for notification in notifications
                ]
            if reminder:
                reminderDTO = ReminderSettingDTO(
                    activity_incomplete=reminder.activity_incomplete,
                    reminder_time=HourMinute(
                        hours=reminder.reminder_time.hour,
                        minutes=reminder.reminder_time.minute,
                    ),
                )
            notificationSettings = NotificationDTO(notifications=notificationsDTO, reminder=reminderDTO)

        return ScheduleEventDto(
            id=event.id,
            entityId=event.activity_id if event.activity_id else event.flow_id,
            timers=timers,
            availabilityType=availabilityType,
            availability=availability,
            selectedDate=event.periodicity.selected_date,
            notificationSettings=notificationSettings,
        )

    async def get_events_by_user_and_applet(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> PublicEventByUser:
        """Get all events for user in applet."""

        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        if not (
            await AppletsCRUD(self.session).get_applet_by_roles(
                user_id=user_id,
                applet_id=applet_id,
                roles=Role.as_list(),
            )
        ):
            raise AccessDeniedToApplet()

        user_events = await EventCRUD(self.session).get_all_by_applet_and_user(
            applet_id=applet_id,
            user_id=user_id,
        )

        general_events = await EventCRUD(self.session).get_general_events_by_user(applet_id=applet_id, user_id=user_id)

        events = PublicEventByUser(
            applet_id=applet_id,
            events=[
                self._convert_to_dto(
                    event=event,
                    notifications=await NotificationCRUD(self.session).get_all_by_event_id(event.id),
                    reminder=await ReminderCRUD(self.session).get_by_event_id(event.id),
                )
                for event in (user_events + general_events)
            ],
        )

        return events

    async def count_events_by_user(self, user_id: uuid.UUID) -> int:
        """Count all events for user in applets that user is respondent."""
        applets = await AppletsCRUD(self.session).get_applets_by_roles(
            user_id=user_id,
            roles=Role.as_list(),
            query_params=QueryParams(),
        )
        applet_ids = [applet.id for applet in applets]
        count = 0

        for applet_id in applet_ids:
            count_user_events = await EventCRUD(self.session).count_individual_events_by_user(
                applet_id=applet_id, user_id=user_id
            )

            count_general_events = await EventCRUD(self.session).count_general_events_by_user(
                applet_id=applet_id, user_id=user_id
            )

            count += count_general_events + count_user_events

        return count

    async def _get_notifications_and_reminder(self, event_id: uuid.UUID) -> PublicNotification | None:
        """Get notifications and reminder for event."""
        notifications = await NotificationCRUD(self.session).get_all_by_event_id(event_id=event_id)

        reminder = await ReminderCRUD(self.session).get_by_event_id(event_id=event_id)

        return (
            PublicNotification(
                notifications=[
                    PublicNotificationSetting(
                        **notification.dict(),
                    )
                    for notification in notifications
                ]
                if notifications
                else None,
                reminder=PublicReminderSetting.from_orm(reminder) if reminder else None,
            )
            if notifications or reminder
            else None
        )

    async def _validate_applet(self, applet_id: uuid.UUID):
        # Check if applet exists
        applet_exist = await AppletsCRUD(self.session).exist_by_id(id_=applet_id)
        if not applet_exist:
            raise AppletNotFoundError(key="id", value=str(applet_id))

    async def _validate_public_applet(self, key: uuid.UUID) -> uuid.UUID:
        # Check if applet exists
        applet = await AppletsCRUD(self.session).get_by_key(key)
        if not applet:
            raise AppletNotFoundError(key="key", value=str(key))
        return applet.id

    async def _validate_user(self, user_id: uuid.UUID):
        # Check if user exists
        user_exist = await UsersCRUD(self.session).exist_by_id(id_=user_id)
        if not user_exist:
            raise UserNotFound(message=f"No such user with id={user_id}.")

    async def _validate_existing_alwaysavailable(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID | None,
        flow_id: uuid.UUID | None,
        respondent_id: uuid.UUID | None,
    ):
        event_schemas = []

        if activity_id:
            event_schemas = await EventCRUD(self.session).get_all_by_applet_and_activity(
                applet_id,
                activity_id,
                respondent_id,
                True,
            )
        elif flow_id:
            event_schemas = await EventCRUD(self.session).get_all_by_applet_and_flow(
                applet_id,
                flow_id,
                respondent_id,
                True,
            )
        if event_schemas:
            raise EventAlwaysAvailableExistsError

    async def remove_individual_calendar(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> None:
        """Remove individual calendar for user in applet."""
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        # Check if user exists
        await self._validate_user(user_id=user_id)

        # Get list of event_ids for user and delete them all
        event_schemas = await EventCRUD(self.session).get_all_by_applet_and_user(applet_id, user_id)
        event_ids = [event_schema.id for event_schema in event_schemas]
        periodicity_ids = [event_schema.periodicity.id for event_schema in event_schemas]
        if not event_ids:
            raise ScheduleNotFoundError()

        await self._delete_by_ids(
            event_ids,
            periodicity_ids,
            user_id,
        )

    async def import_schedule(self, schedules: list[EventRequest], applet_id: uuid.UUID) -> list[PublicEvent]:
        """Import schedule."""
        events = []
        for schedule in schedules:
            if schedule.periodicity.type == PeriodicityType.ALWAYS:
                # delete alwaysAvailable events of this activity or flow,
                # if new event type is AA
                await self._delete_by_activity_or_flow(
                    applet_id=applet_id,
                    activity_id=schedule.activity_id,
                    flow_id=schedule.flow_id,
                    respondent_id=schedule.respondent_id,
                    only_always_available=True,
                )
            event = await self.create_schedule(applet_id=applet_id, schedule=schedule)
            events.append(event)

        return events

    async def create_schedule_individual(self, applet_id: uuid.UUID, respondent_id: uuid.UUID) -> list[PublicEvent]:
        """Create individual schedule for a user for the first time"""
        # get list of activity ids
        activity_ids = []
        activities = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id, is_reviewable=False)
        activity_ids = [activity.id for activity in activities if not activity.is_hidden]

        # get list of flow ids
        flow_ids = []
        flows = await FlowsCRUD(self.session).get_by_applet_id(applet_id)
        flow_ids = [flow.id for flow in flows if not flow.is_hidden]

        # create default events
        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=activity_ids,
            is_activity=True,
            respondent_id=respondent_id,
        )

        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=flow_ids,
            is_activity=False,
            respondent_id=respondent_id,
        )

        # get all events for user
        return await self.get_all_schedules(
            applet_id,
            QueryParams(filters={"respondent_id": respondent_id}),
        )

    async def create_default_schedules_if_not_exist(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID],
    ) -> None:
        """Create default schedules for applet."""
        activities_without_events = await ActivityEventsCRUD(self.session).get_missing_events(activity_ids)
        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=activities_without_events,
            is_activity=True,
        )

    async def get_default_respondents(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        default_respondents = await EventCRUD(self.session).get_default_schedule_user_ids_by_applet_id(applet_id)
        return default_respondents
