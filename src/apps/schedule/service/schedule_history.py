__all__ = ["ScheduleHistoryService"]

import uuid

from apps.applets.crud import AppletsCRUD
from apps.schedule.crud.schedule_history import (
    AppletEventsCRUD,
    NotificationHistoryCRUD,
    ReminderHistoryCRUD,
    ScheduleHistoryCRUD,
)
from apps.schedule.crud.user_device_events_history import UserDeviceEventsHistoryCRUD
from apps.schedule.db.schemas import (
    AppletEventsSchema,
    EventHistorySchema,
    NotificationHistorySchema,
    ReminderHistorySchema,
)
from apps.schedule.domain.constants import EventType
from apps.schedule.domain.schedule.internal import ScheduleEvent
from apps.schedule.domain.schedule.public import ExportDeviceHistoryDto, ExportEventHistoryDto
from apps.shared.query_params import QueryParams


class ScheduleHistoryService:
    def __init__(self, session):
        self.session = session

    async def get_by_id(self, id_version: str) -> EventHistorySchema | None:
        return await ScheduleHistoryCRUD(self.session).get_by_id(id_version)

    async def add_history(self, applet_id: uuid.UUID, event: ScheduleEvent, updated_by: uuid.UUID | None) -> None:
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)

        # Refresh the applet so we don't get the old version number, in case the version has changed
        await self.session.refresh(applet)

        event_history = await ScheduleHistoryCRUD(self.session).add(
            EventHistorySchema(
                start_time=event.start_time,
                end_time=event.end_time,
                access_before_schedule=event.access_before_schedule,
                one_time_completion=event.one_time_completion,
                timer=event.timer,
                timer_type=event.timer_type,
                version=event.version,
                periodicity=event.periodicity,
                start_date=event.start_date,
                end_date=event.end_date,
                selected_date=event.selected_date,
                id_version=f"{event.id}_{event.version}",
                id=event.id,
                event_type=EventType.ACTIVITY if event.activity_id else EventType.FLOW,
                activity_id=event.activity_id,
                activity_flow_id=event.flow_id,
                user_id=event.user_id,
                updated_by=updated_by,
            )
        )

        await AppletEventsCRUD(self.session).add(
            AppletEventsSchema(applet_id=f"{applet_id}_{applet.version}", event_id=event_history.id_version)
        )

        if event.notifications:
            await NotificationHistoryCRUD(self.session).add_many(
                [
                    NotificationHistorySchema(
                        from_time=notification.from_time,
                        to_time=notification.to_time,
                        at_time=notification.at_time,
                        trigger_type=notification.trigger_type,
                        order=notification.order,
                        id_version=f"{notification.id}_{event.version}",
                        id=notification.id,
                        event_id=event_history.id_version,
                    )
                    for notification in event.notifications
                ]
            )

        if event.reminder:
            await ReminderHistoryCRUD(self.session).add(
                ReminderHistorySchema(
                    activity_incomplete=event.reminder.activity_incomplete,
                    reminder_time=event.reminder.reminder_time,
                    id_version=f"{event.reminder.id}_{event.version}",
                    id=event.reminder.id,
                    event_id=event_history.id_version,
                )
            )

    async def mark_as_deleted(self, events: list[tuple[uuid.UUID, str]]) -> None:
        if len(events) == 0:
            return

        await ScheduleHistoryCRUD(self.session).mark_as_deleted(events)

    async def update_applet_event_links(
        self,
        applet_id: uuid.UUID,
        current_applet_version: str,
        new_applet_version: str,
    ):
        """
        Make new entries into `applet_events` to link a new version of an applet to the existing version of its events.
        This method is useful when an applet has its version bumped and the events are not updated. The previous entries
        in `applet_events` are not removed to maintain the history of the applet.
        """

        crud = AppletEventsCRUD(self.session)
        applet_event_schemas = await crud.find_by_applet_id_version(f"{applet_id}_{current_applet_version}")

        if len(applet_event_schemas) > 0:
            await crud.add_many(
                [
                    AppletEventsSchema(applet_id=f"{applet_id}_{new_applet_version}", event_id=schema.event_id)
                    for schema in applet_event_schemas
                ]
            )

    async def retrieve_applet_all_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportEventHistoryDto], int]:
        event_history, total = await ScheduleHistoryCRUD(self.session).retrieve_applet_all_events_history(
            applet_id, query_params
        )

        return event_history, total

    async def retrieve_applet_all_device_events_history(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[ExportDeviceHistoryDto], int]:
        return await UserDeviceEventsHistoryCRUD(self.session).retrieve_applet_all_device_events_history(
            applet_id, query_params
        )
