import asyncio
import calendar
import codecs
import csv
import datetime
import io
import uuid
from functools import wraps
from typing import Any, cast

import typer
from pydantic import parse_obj_as
from sqlalchemy import Date, and_, case, false, literal, null, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.applets.db.schemas import AppletSchema
from apps.schedule.db.schemas import EventSchema, FlowEventsSchema, PeriodicitySchema, UserEventsSchema
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.domain.base import PublicModel
from apps.workspaces.db.schemas.user_applet_access import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database import session_manager
from infrastructure.dependency.cdn import get_operations_bucket
from infrastructure.utility import CDNClient

app = typer.Typer()

APPLET_ID = "64c975a4-22d8-180c-f9b3-e42600000000"
PATH_PREFIX = "export-ami"
PATH_FLOW_FILE_NAME = "daily-user-flow-schedule.csv"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


# Not ISO
MONDAY_WEEKDAY = 0
FRIDAY_WEEKDAY = 4
SATURDAY_WEEKDAY = 5
SUNDAY_WEEKDAY = 6

OUTPUT_DATE_FORMAT = "%m/%d"
OUTPUT_TIME_FORMAT = "%H:%M"


def is_last_day_of_month(date: datetime.date):
    mdays = calendar.mdays.copy()  # type: ignore[attr-defined]
    if calendar.isleap(date.year):
        mdays[calendar.February] += 1  # type: ignore[attr-defined]
    return date.day == mdays[date.month]


class OutputRow(PublicModel):
    applet_id: uuid.UUID
    date_prior_day: str
    user_id: uuid.UUID
    flow_id: uuid.UUID
    flow_name: str
    applet_version: str
    scheduled_date: str
    schedule_start_time: str
    schedule_end_time: str
    # TODO: remove after debug
    event_id: uuid.UUID


class RawRow(PublicModel):
    applet_id: uuid.UUID
    date: datetime.date
    user_id: uuid.UUID
    flow_id: uuid.UUID
    flow_name: str
    applet_version: str
    schedule_start_time: datetime.time
    schedule_end_time: datetime.time
    event_id: uuid.UUID
    event_type: PeriodicityType
    start_date: datetime.date | None
    end_date: datetime.date | None
    selected_date: datetime.date

    @property
    def is_crossday_event(self) -> bool:
        return self.schedule_start_time > self.schedule_end_time


async def save_csv(path: str, data: list[dict[str, Any]], cdn_client: CDNClient) -> None:
    if data:
        columns = list(data[0].keys())

        fin = io.BytesIO()
        StreamWriter = codecs.getwriter("utf-8")
        f_wrapper = StreamWriter(fin)

        writer = csv.DictWriter(f_wrapper, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        fin.seek(0)
        await cdn_client.upload(path, fin)


async def get_user_flow_events(session: AsyncSession, run_date: datetime.date) -> list[RawRow]:
    cte = (
        select(
            EventSchema.applet_id,
            EventSchema.id.label("event_id"),
            UserEventsSchema.user_id,
            FlowEventsSchema.flow_id,
            PeriodicitySchema.type.label("event_type"),
            case(
                (
                    PeriodicitySchema.type.in_(("ALWAYS", "WEEKDAYS", "DAILY")),
                    run_date,
                ),
                (PeriodicitySchema.type.in_(("WEEKLY", "MONTHLY")), PeriodicitySchema.start_date),
                else_=PeriodicitySchema.selected_date,
            ).label("selected_date"),
            PeriodicitySchema.start_date,
            PeriodicitySchema.end_date,
            EventSchema.start_time,
            EventSchema.end_time,
        )
        .select_from(EventSchema)
        .join(UserEventsSchema, UserEventsSchema.event_id == EventSchema.id)
        .join(PeriodicitySchema, PeriodicitySchema.id == EventSchema.periodicity_id)
        .join(FlowEventsSchema, FlowEventsSchema.event_id == EventSchema.id)
        .where(EventSchema.is_deleted == false())
    ).cte("user_flow_events")

    query = (
        select(
            AppletSchema.id.label("applet_id"),
            literal(run_date, Date).label("date"),
            UserAppletAccessSchema.user_id.label("user_id"),
            ActivityFlowSchema.id.label("flow_id"),
            ActivityFlowSchema.name.label("flow_name"),
            AppletSchema.version.label("applet_version"),
            cte.c.event_id.label("event_id"),
            cte.c.event_type.label("event_type"),
            cte.c.selected_date.label("selected_date"),
            cte.c.start_date.label("start_date"),
            cte.c.end_date.label("end_date"),
            cte.c.start_time.label("schedule_start_time"),
            cte.c.end_time.label("schedule_end_time"),
        )
        .select_from(AppletSchema)
        .join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.applet_id == AppletSchema.id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            ),
        )
        .join(ActivityFlowSchema, ActivityFlowSchema.applet_id == AppletSchema.id)
        .outerjoin(
            cte,
            and_(
                cte.c.applet_id == AppletSchema.id,
                cte.c.user_id == UserAppletAccessSchema.user_id,
                cte.c.flow_id == ActivityFlowSchema.id,
            ),
        )
        .where(
            AppletSchema.id == uuid.UUID(APPLET_ID),
            cte.c.event_id != null(),
            ActivityFlowSchema.is_hidden == false(),
        )
        .order_by(UserAppletAccessSchema.user_id, ActivityFlowSchema.name)
    )
    db_result = await session.execute(query)
    result = db_result.mappings().all()
    return parse_obj_as(list[RawRow], result)


def filter_events(raw_events_rows: list[RawRow], schedule_date: datetime.date) -> list[RawRow]:  # noqa: C901
    filtered: list[RawRow] = []
    for row in raw_events_rows:
        match row.event_type:
            case PeriodicityType.ALWAYS:
                filtered.append(row)
            case PeriodicityType.DAILY:
                row.end_date = cast(datetime.date, row.end_date)
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                if schedule_date <= row.end_date:
                    filtered.append(row)
            case PeriodicityType.ONCE:
                schedule_start_date = row.selected_date
                row.end_date = row.selected_date
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                if schedule_date >= schedule_start_date and schedule_date < row.end_date:
                    filtered.append(row)
            # TODO: patch events with periodicity WEEKDAYS, WEEKLY, some events don't have start_date and end_date
            # (the issue is in migrated data).
            # For current script is ok, because or applet does not have issues with WEEKDAYS, WEEKLY
            case PeriodicityType.WEEKDAYS:
                row.end_date = cast(datetime.date, row.end_date)
                row.start_date = cast(datetime.date, row.start_date)
                last_weekday = FRIDAY_WEEKDAY
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                    last_weekday = SATURDAY_WEEKDAY
                if schedule_date.weekday() <= last_weekday and schedule_date <= row.end_date:
                    filtered.append(row)
            case PeriodicityType.WEEKLY:
                row.end_date = cast(datetime.date, row.end_date)
                row.start_date = cast(datetime.date, row.start_date)
                scheduled_weekday = row.start_date.weekday()
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                    scheduled_weekday += 1
                    # If was SUNDAY start new week
                    if scheduled_weekday > SUNDAY_WEEKDAY:
                        scheduled_weekday = 0
                if schedule_date.weekday() == scheduled_weekday and schedule_date <= row.end_date:
                    filtered.append(row)
            case PeriodicityType.MONTHLY:
                row.end_date = cast(datetime.date, row.end_date)
                row.start_date = cast(datetime.date, row.start_date)
                scheduled_monthday = row.start_date.day
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                if is_last_day_of_month(row.start_date):
                    if (
                        schedule_date.day == scheduled_monthday or schedule_date.day == 1
                    ) and schedule_date < row.end_date:
                        filtered.append(row)
                elif schedule_date.day == scheduled_monthday and schedule_date.day <= row.end_date.day:
                    filtered.append(row)
    return filtered


@app.command(short_help="Export daily user flow schedule events to csv")
@coro
async def generate_schedule(run_date: datetime.datetime = typer.Argument(..., help="run date")):
    scheduled_date = run_date.date() - datetime.timedelta(days=1)
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        raw_data = await get_user_flow_events(session, scheduled_date)
    print(f"Num raw rows is {len(raw_data)}")
    filtered = filter_events(raw_data, scheduled_date)
    print(f"Num filtered rows is {len(filtered)}")
    result = []
    for row in filtered:
        outrow = OutputRow(
            applet_id=row.applet_id,
            date_prior_day=row.date.strftime(OUTPUT_DATE_FORMAT),
            user_id=row.user_id,
            flow_id=row.flow_id,
            flow_name=row.flow_name,
            applet_version=row.applet_version,
            scheduled_date=scheduled_date.strftime(OUTPUT_DATE_FORMAT),
            schedule_start_time=row.schedule_start_time.strftime(OUTPUT_TIME_FORMAT),
            schedule_end_time=row.schedule_end_time.strftime(OUTPUT_TIME_FORMAT),
            event_id=row.event_id,
        ).dict()
        result.append(outrow)
    cdn_client = await get_operations_bucket()
    path = cdn_client.generate_key(PATH_PREFIX, str(APPLET_ID), PATH_FLOW_FILE_NAME)
    await save_csv(path, result, cdn_client)
