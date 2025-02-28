import asyncio
import uuid
from datetime import date

from apps.activities.crud import ActivitiesCRUD
from apps.activity_flows.crud import FlowsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.errors import AppletNotFoundError
from apps.schedule.crud.events import EventCRUD
from apps.schedule.crud.notification import NotificationCRUD, ReminderCRUD
from apps.schedule.crud.schedule_history import NotificationHistoryCRUD, ReminderHistoryCRUD
from apps.schedule.crud.user_device_events_history import UserDeviceEventsHistoryCRUD
from apps.schedule.db.schemas import EventSchema, NotificationSchema
from apps.schedule.domain.constants import DefaultEvent, EventType, PeriodicityType
from apps.schedule.domain.schedule import BaseEvent
from apps.schedule.domain.schedule.internal import (
    Event,
    EventCreate,
    EventFull,
    EventUpdate,
    NotificationSetting,
    ReminderSetting,
    ReminderSettingCreate,
    ScheduleEvent,
)
from apps.schedule.domain.schedule.public import (
    ExportDeviceHistoryDto,
    ExportEventHistoryDto,
    PublicEvent,
    PublicEventByUser,
    PublicEventCount,
    PublicNotification,
    PublicNotificationSetting,
    PublicPeriodicity,
    PublicReminderSetting,
)
from apps.schedule.domain.schedule.requests import EventRequest, EventUpdateRequest
from apps.schedule.errors import (
    AccessDeniedToApplet,
    ActivityOrFlowNotFoundError,
    EventAlwaysAvailableExistsError,
    ScheduleNotFoundError,
)
from apps.schedule.service.schedule_history import ScheduleHistoryService
from apps.shared.query_params import QueryParams
from apps.users.cruds.user import UsersCRUD
from apps.users.errors import UserNotFound
from apps.workspaces.domain.constants import Role

__all__ = ["ScheduleService"]


class ScheduleService:
    def __init__(self, session, admin_user_id: uuid.UUID | None = None):
        self.session = session
        self.admin_user_id = admin_user_id

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

        # Create event
        # The version number will be autogenerated
        event: Event = await EventCRUD(self.session).save(
            EventCreate(
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                access_before_schedule=schedule.access_before_schedule,
                one_time_completion=schedule.one_time_completion,
                timer=schedule.timer,
                timer_type=schedule.timer_type,
                applet_id=applet_id,
                periodicity=schedule.periodicity.type,
                start_date=schedule.periodicity.start_date,
                end_date=schedule.periodicity.end_date,
                selected_date=schedule.periodicity.selected_date,
                user_id=schedule.respondent_id,
                activity_id=schedule.activity_id,
                activity_flow_id=schedule.flow_id,
                event_type=EventType.ACTIVITY if schedule.activity_id else EventType.FLOW,
            )
        )

        schedule_event = ScheduleEvent(
            **event.dict(exclude={"applet_id", "activity_flow_id"}),
            flow_id=event.activity_flow_id,
        )

        # Create notification and reminder
        if schedule.notification:
            notifications: list[NotificationSetting] | None = None
            reminder: ReminderSetting | None = None

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
                schedule_event.notifications = notifications

            if schedule.notification.reminder:
                reminder = await ReminderCRUD(self.session).create(
                    ReminderSettingCreate(
                        event_id=event.id,
                        activity_incomplete=schedule.notification.reminder.activity_incomplete,  # noqa: E501
                        reminder_time=schedule.notification.reminder.reminder_time,  # noqa: E501
                    )
                )
                schedule_event.reminder = reminder

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

        await ScheduleHistoryService(self.session).add_history(
            event=schedule_event, applet_id=applet_id, updated_by=self.admin_user_id
        )

        return PublicEvent(
            **event.dict(exclude={"periodicity"}),
            periodicity=PublicPeriodicity(
                type=event.periodicity,
                start_date=event.start_date,
                end_date=event.end_date,
                selected_date=event.selected_date,
            ),
            respondent_id=schedule.respondent_id,
            flow_id=schedule.flow_id,
            notification=notification_public if schedule.notification else None,
        )

    async def get_schedule_by_id(self, schedule_id: uuid.UUID, applet_id: uuid.UUID) -> PublicEvent:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event: Event = await EventCRUD(self.session).get_by_id(pk=schedule_id)
        notification = await self._get_notifications_and_reminder(event.id)

        return PublicEvent(
            **event.dict(exclude={"periodicity", "user_id", "activity_flow_id"}),
            periodicity=PublicPeriodicity(
                type=event.periodicity,
                start_date=event.start_date,
                end_date=event.end_date,
                selected_date=event.selected_date,
            ),
            respondent_id=event.user_id,
            flow_id=event.activity_flow_id,
            notification=notification,
        )

    async def get_all_schedules(self, applet_id: uuid.UUID, query: QueryParams | None = None) -> list[PublicEvent]:
        # validate respondent_id if present
        if query is not None and "respondent_id" in query.filters:
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
            notification = await self._get_notifications_and_reminder(event.id)

            events.append(
                PublicEvent(
                    **event.dict(exclude={"periodicity", "user_id", "activity_flow_id"}),
                    periodicity=PublicPeriodicity(
                        type=event.periodicity,
                        start_date=event.start_date,
                        end_date=event.end_date,
                        selected_date=event.selected_date,
                    ),
                    respondent_id=event.user_id,
                    flow_id=event.activity_flow_id,
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
            base_event = BaseEvent(**event.dict())

            full_events.append(
                EventFull(
                    id=event.id,
                    **base_event.dict(),
                    periodicity=event.periodicity,
                    start_date=event.start_date,
                    end_date=event.end_date,
                    selected_date=event.selected_date,
                    activity_id=event.activity_id,
                    flow_id=event.activity_flow_id,
                    user_id=event.user_id,
                    version=event.version,
                    event_type=event.event_type,
                )
            )

        events = PublicEventByUser(
            applet_id=applet_id,
            events=[
                ScheduleEvent(
                    **full_event.dict(),
                    notifications=await NotificationCRUD(self.session).get_all_by_event_id(full_event.id),
                    reminder=await ReminderCRUD(self.session).get_by_event_id(full_event.id),
                ).to_schedule_event_dto()
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

        await self._delete_by_ids(event_ids)

        await ScheduleHistoryService(self.session).mark_as_deleted(
            [(event.id, event.version) for event in event_schemas]
        )

        # Create default events for activities and flows
        processed_activities_and_flows: dict[uuid.UUID, bool] = {}
        for event in event_schemas:
            if event.activity_id and event.activity_id not in processed_activities_and_flows:
                await self._create_default_event(
                    applet_id=applet_id,
                    activity_id=event.activity_id,
                    is_activity=True,
                    respondent_id=event.user_id,
                )
                processed_activities_and_flows[event.activity_id] = True
            if event.activity_flow_id and event.activity_flow_id not in processed_activities_and_flows:
                await self._create_default_event(
                    applet_id=applet_id,
                    activity_id=event.activity_flow_id,
                    is_activity=False,
                    respondent_id=event.user_id,
                )
                processed_activities_and_flows[event.activity_flow_id] = True

    async def delete_schedule_by_id(self, schedule_id: uuid.UUID) -> uuid.UUID | None:
        crud = EventCRUD(self.session)
        event: Event = await crud.get_by_id(pk=schedule_id)

        await self._delete_by_ids(event_ids=[schedule_id])

        await ScheduleHistoryService(self.session).mark_as_deleted([(event.id, event.version)])

        # Create default event for activity or flow if another event doesn't exist
        if event.activity_id:
            count_events = await crud.count_by_activity(activity_id=event.activity_id, respondent_id=event.user_id)
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=event.activity_id,
                    is_activity=True,
                    respondent_id=event.user_id,
                )

        elif event.activity_flow_id:
            count_events = await crud.count_by_flow(flow_id=event.activity_flow_id, respondent_id=event.user_id)
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=event.activity_flow_id,
                    is_activity=False,
                    respondent_id=event.user_id,
                )
        return event.user_id

    async def update_schedule(
        self,
        applet_id: uuid.UUID,
        schedule_id: uuid.UUID,
        schedule: EventUpdateRequest,
    ) -> PublicEvent:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        event: Event = await EventCRUD(self.session).get_by_id(pk=schedule_id)

        # Delete all events of this activity or flow
        # if new periodicity type is "always" and old periodicity type is not "always"
        if schedule.periodicity.type == PeriodicityType.ALWAYS and event.periodicity != PeriodicityType.ALWAYS:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id,
                activity_id=event.activity_id,
                flow_id=event.activity_flow_id,
                respondent_id=event.user_id,
                only_always_available=False,
                except_event_id=schedule_id,
            )

        old_event_version = event.version

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
                applet_id=applet_id,
                periodicity=schedule.periodicity.type,
                start_date=schedule.periodicity.start_date,
                end_date=schedule.periodicity.end_date,
                selected_date=schedule.periodicity.selected_date,
                event_type=event.event_type,
                activity_id=event.activity_id,
                activity_flow_id=event.activity_flow_id,
                user_id=event.user_id,
            ),
        )

        schedule_event = ScheduleEvent(
            **event.dict(exclude={"applet_id", "activity_flow_id"}),
            flow_id=event.activity_flow_id,
        )

        # Update notification
        await NotificationCRUD(self.session).delete_by_event_ids([schedule_id])
        await ReminderCRUD(self.session).delete_by_event_ids([schedule_id])

        await asyncio.gather(
            NotificationHistoryCRUD(self.session).mark_as_deleted([(event.id, old_event_version)]),
            ReminderHistoryCRUD(self.session).mark_as_deleted([(event.id, old_event_version)]),
        )

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
                schedule_event.notifications = notifications

            if schedule.notification.reminder:
                reminder = await ReminderCRUD(self.session).create(
                    reminder=ReminderSettingCreate(
                        event_id=event.id,
                        activity_incomplete=schedule.notification.reminder.activity_incomplete,
                        reminder_time=schedule.notification.reminder.reminder_time,
                    )
                )
                schedule_event.reminder = reminder

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

        await ScheduleHistoryService(self.session).add_history(
            event=schedule_event,
            applet_id=applet_id,
            updated_by=self.admin_user_id,
        )

        return PublicEvent(
            **event.dict(exclude={"periodicity", "user_id", "activity_flow_id"}),
            periodicity=PublicPeriodicity(
                type=event.periodicity,
                start_date=event.start_date,
                end_date=event.end_date,
                selected_date=event.selected_date,
            ),
            respondent_id=event.user_id,
            flow_id=event.activity_flow_id,
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
        activity_counts, flow_counts = await EventCRUD(self.session).count_by_applet(applet_id=applet_id)

        event_count.activity_events = activity_counts if activity_counts else []
        event_count.flow_events = flow_counts if flow_counts else []

        return event_count

    async def delete_by_user_id(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> None:
        # Check if applet exists
        await self._validate_applet(applet_id=applet_id)

        # Check if user exists
        await self._validate_user(user_id=user_id)

        event_schemas = await EventCRUD(self.session).get_all_by_applet_and_user(applet_id, user_id)

        # List of event_ids for user for deletion
        event_ids: list[uuid.UUID] = []
        activity_ids: set[uuid.UUID] = set()
        flow_ids: set[uuid.UUID] = set()

        for event in event_schemas:
            event_ids.append(event.id)
            if event.activity_id:
                activity_ids.add(event.activity_id)
            if event.flow_id:
                flow_ids.add(event.flow_id)

        if not event_ids:
            raise ScheduleNotFoundError()
        await self._delete_by_ids(event_ids=event_ids)

        await ScheduleHistoryService(self.session).mark_as_deleted(
            [(event.id, event.version) for event in event_schemas]
        )

        # Create always available events for all activities and flows
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

        event_ids = [event.id for event in event_schemas if event.id != except_event_id]

        if event_ids:
            await self._delete_by_ids(event_ids=event_ids)
            await ScheduleHistoryService(self.session).mark_as_deleted(
                [(event.id, event.version) for event in event_schemas]
            )

    async def _delete_by_ids(
        self,
        event_ids: list[uuid.UUID],
    ):
        await NotificationCRUD(self.session).delete_by_event_ids(event_ids)
        await ReminderCRUD(self.session).delete_by_event_ids(event_ids)
        await EventCRUD(self.session).delete_by_ids(event_ids)

    async def delete_by_activity_ids(self, applet_id: uuid.UUID, activity_ids: list[uuid.UUID]) -> None:
        """Delete schedules by activity ids."""
        events = await EventCRUD(self.session).get_all_by_activity_flow_ids(applet_id, activity_ids, True)
        event_ids = [event.id for event in events]
        await self._delete_by_ids(event_ids)
        await ScheduleHistoryService(self.session).mark_as_deleted([(event.id, event.version) for event in events])

    async def delete_by_flow_ids(self, applet_id: uuid.UUID, flow_ids: list[uuid.UUID]) -> None:
        """Delete schedules by flow ids."""
        events = await EventCRUD(self.session).get_all_by_activity_flow_ids(applet_id, flow_ids, False)
        event_ids = [event.id for event in events]
        await self._delete_by_ids(event_ids)
        await ScheduleHistoryService(self.session).mark_as_deleted([(event.id, event.version) for event in events])

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
        events = []

        for applet in applets:
            user_events = await EventCRUD(self.session).get_all_by_applet_and_user(
                applet_id=applet.id,
                user_id=user_id,
            )
            general_events = await EventCRUD(self.session).get_general_events_by_user(
                applet_id=applet.id, user_id=user_id
            )
            all_events = user_events + general_events
            events.append(
                PublicEventByUser(
                    applet_id=applet.id,
                    events=[
                        ScheduleEvent(
                            **event.dict(),
                            notifications=await NotificationCRUD(self.session).get_all_by_event_id(event.id),
                            reminder=await ReminderCRUD(self.session).get_by_event_id(event.id),
                        ).to_schedule_event_dto()
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
        device_id: str | None = None,
        os_name: str | None = None,
        os_version: str | None = None,
        app_version: str | None = None,
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
        full_events_map: dict[uuid.UUID, list[EventFull]] = self._sum_applets_events_map(
            user_events_map, general_events_map
        )

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
                        ScheduleEvent(
                            **event.dict(),
                            notifications=notifications_map.get(event.id),
                            reminder=reminders_map.get(event.id),
                        ).to_schedule_event_dto()
                        for event in all_events
                    ],
                )
            )

        if device_id:
            all_events = [event for value in full_events_map.values() for event in value]
            await UserDeviceEventsHistoryCRUD(self.session).record_event_versions(
                user_id=user_id,
                device_id=device_id,
                event_versions=[(event.id, event.version) for event in all_events],
                os_name=os_name,
                os_version=os_version,
                app_version=app_version,
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
                ScheduleEvent(
                    **event.dict(),
                    notifications=await NotificationCRUD(self.session).get_all_by_event_id(event.id),
                    reminder=await ReminderCRUD(self.session).get_by_event_id(event.id),
                ).to_schedule_event_dto()
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
        applet = await AppletsCRUD(self.session).get_by_link(key)
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
        existing_always_available = await EventCRUD(self.session).validate_existing_always_available(
            applet_id,
            activity_id,
            flow_id,
            respondent_id,
        )
        if existing_always_available:
            raise EventAlwaysAvailableExistsError

    async def remove_individual_calendar(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> None:
        """Remove individual calendar for user in applet."""
        # Check if user exists
        await self._validate_user(user_id=user_id)

        # Get list of event_ids for user and delete them all
        event_schemas = await EventCRUD(self.session).get_all_by_applet_and_user(applet_id, user_id)
        event_ids = [event_schema.id for event_schema in event_schemas]
        if not event_ids:
            raise ScheduleNotFoundError()

        await self._delete_by_ids(event_ids=event_ids)

        await ScheduleHistoryService(self.session).mark_as_deleted(
            [(event.id, event.version) for event in event_schemas]
        )

    async def import_schedule(self, event_requests: list[EventRequest], applet_id: uuid.UUID) -> list[PublicEvent]:
        """Import schedule."""
        events = []
        for event_request in event_requests:
            if event_request.periodicity.type == PeriodicityType.ALWAYS:
                # delete alwaysAvailable events of this activity or flow,
                # if new event type is AA
                await self._delete_by_activity_or_flow(
                    applet_id=applet_id,
                    activity_id=event_request.activity_id,
                    flow_id=event_request.flow_id,
                    respondent_id=event_request.respondent_id,
                    only_always_available=True,
                )
            event = await self.create_schedule(applet_id=applet_id, schedule=event_request)
            events.append(event)

        return events

    async def create_schedule_individual(self, applet_id: uuid.UUID, respondent_id: uuid.UUID) -> list[PublicEvent]:
        """Create individual schedule for a user for the first time"""
        # get list of activity ids
        activities = await ActivitiesCRUD(self.session).get_by_applet_id(applet_id, is_reviewable=False)
        activity_ids = [activity.id for activity in activities if not activity.is_hidden]

        # get list of flow ids
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
        activities_without_events = await EventCRUD(self.session).get_activities_without_events(activity_ids)
        await self.create_default_schedules(
            applet_id=applet_id,
            activity_ids=activities_without_events,
            is_activity=True,
        )

    async def get_default_respondents(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        default_respondents = await EventCRUD(self.session).get_default_schedule_user_ids_by_applet_id(applet_id)
        return default_respondents

    async def retrieve_applet_all_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportEventHistoryDto], int]:
        return await ScheduleHistoryService(self.session).retrieve_applet_all_events_history(applet_id, query_params)

    async def retrieve_applet_all_device_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportDeviceHistoryDto], int]:
        return await UserDeviceEventsHistoryCRUD(self.session).retrieve_applet_all_device_events_history(
            applet_id, query_params
        )
