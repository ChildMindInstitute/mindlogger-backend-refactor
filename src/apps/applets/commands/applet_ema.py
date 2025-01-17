import calendar
import codecs
import csv
import datetime
import io
import os
import tracemalloc
import uuid
from typing import BinaryIO, Optional, TypeVar, cast

import typer
from pydantic import parse_obj_as
from rich import print
from sqlalchemy import Date, and_, case, false, func, literal, null, select, text
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.db.schemas import ActivityHistorySchema as ActivityHistory
from apps.activities.db.schemas import ActivitySchema
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema as FlowHistory
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema as FlowItemHistory
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.applets.db.schemas import AppletSchema
from apps.job.constants import JobStatus
from apps.job.errors import JobStatusError
from apps.job.service import JobService
from apps.schedule.db.schemas import (
    ActivityEventsSchema,
    EventSchema,
    FlowEventsSchema,
    PeriodicitySchema,
    UserEventsSchema,
)
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.domain.base import PublicModel
from apps.subjects.db.schemas import SubjectSchema
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas.user_applet_access import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from config import settings
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager
from infrastructure.dependency.cdn import get_operations_bucket
from infrastructure.utility import CDNClient, ObjectNotFoundError

app = typer.Typer()


APPLET_ID = settings.applet_ema.id
APPLET_NAME = settings.applet_ema.name
PATH_PREFIX = settings.applet_ema.export_path_prefix
PATH_FLOW_FILE_NAME = settings.applet_ema.export_flow_file_name
PATH_USER_FLOW_SCHEDULE_FILE_NAME = settings.applet_ema.export_user_flow_schedule_file_name
PATH_USER_ACTIVITY_SCHEDULE_FILE_NAME = settings.applet_ema.export_user_activity_schedule_file_name


# Not ISO
MONDAY_WEEKDAY = 0
FRIDAY_WEEKDAY = 4
SATURDAY_WEEKDAY = 5
SUNDAY_WEEKDAY = 6

OUTPUT_TIME_FORMAT = "%H:%M"


class FlowEventOutputRow(PublicModel):
    applet_id: uuid.UUID
    date_prior_day: datetime.date
    user_id: uuid.UUID
    secret_user_id: str | uuid.UUID
    flow_id: uuid.UUID
    flow_name: str
    applet_version: str
    scheduled_date: datetime.date
    schedule_start_time: str
    schedule_end_time: str
    # TODO: remove after debug
    event_id: uuid.UUID


class ActivityEventOutputRow(PublicModel):
    applet_id: uuid.UUID
    date_prior_day: datetime.date
    user_id: uuid.UUID
    secret_user_id: str | uuid.UUID
    activity_id: uuid.UUID
    activity_name: str
    applet_version: str
    scheduled_date: datetime.date
    schedule_start_time: str
    schedule_end_time: str
    # TODO: remove after debug
    event_id: uuid.UUID


class RawRow(PublicModel):
    applet_id: uuid.UUID
    date: datetime.date
    user_id: uuid.UUID
    secret_user_id: str | uuid.UUID
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


TRawRow = TypeVar("TRawRow", bound=RawRow)


class FlowEventRawRow(RawRow):
    flow_id: uuid.UUID
    flow_name: str


class ActivityEventRawRow(RawRow):
    activity_id: uuid.UUID
    activity_name: str


def is_last_day_of_month(date: datetime.date):
    mdays = calendar.mdays.copy()  # type: ignore[attr-defined]
    if calendar.isleap(date.year):
        mdays[calendar.FEBRUARY] += 1
    return date.day == mdays[date.month]


def get_applet_id(applet_id: uuid.UUID | None = None) -> uuid.UUID:
    _applet_id = str(applet_id) if applet_id else APPLET_ID
    if not _applet_id:
        print("[bold red]Error: applet export not configured[/bold red]")
        exit(1)
    return uuid.UUID(_applet_id)


def create_csv(data: list[dict], columns: list | None = None, append_to: BinaryIO | None = None) -> BinaryIO | None:
    if data:
        if not columns:
            columns = list(data[0].keys())

        fin = append_to if append_to else io.BytesIO()
        StreamWriter = codecs.getwriter("utf-8")
        f_wrapper = StreamWriter(fin)

        writer = csv.DictWriter(f_wrapper, fieldnames=columns)
        if not fin.tell():
            writer.writeheader()
        writer.writerows(data)
        fin.seek(0)

        return fin
    return None


async def save_csv(path: str, data: list[dict], cdn_client: CDNClient, columns: list | None = None):
    if f := create_csv(data, columns):
        await cdn_client.upload(path, f)


async def _export_flows(applet_id: uuid.UUID, path_prefix: str):
    """
    select
        split_part(fh.applet_id , '_', 1) applet_id,
        fih.created_at flow_item_history_created_date,
        split_part(fh.id_version, '_', 1) flow_id,
        fh."name" flow_name,
        split_part(fh.applet_id , '_', 2) applet_version,
        split_part(ah.id_version, '_', 1) activity_id,
        ah."name" activity_name
    from flow_histories fh
    join flow_item_histories fih on fih.activity_flow_id = fh.id_version
    join activity_histories ah on ah.id_version = fih.activity_id
    where fh.applet_id like '64c975a4-22d8-180c-f9b3-e42600000000_%'
    order by applet_version, fh."order", fih."order"
    """
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        query = (
            select(
                func.split_part(FlowHistory.applet_id, text("'_'"), 1).label("applet_id"),
                FlowItemHistory.created_at.label("flow_item_history_created_date"),
                func.split_part(FlowHistory.id_version, text("'_'"), 1).label("flow_id"),
                FlowHistory.name.label("flow_name"),
                func.split_part(FlowHistory.applet_id, text("'_'"), 2).label("applet_version"),
                func.split_part(ActivityHistory.id_version, text("'_'"), 1).label("activity_id"),
                ActivityHistory.name.label("activity_name"),
            )
            .join(FlowItemHistory, FlowItemHistory.activity_flow_id == FlowHistory.id_version)
            .join(ActivityHistory, ActivityHistory.id_version == FlowItemHistory.activity_id)
            .where(FlowHistory.applet_id.like(f"{applet_id}_%"))
            .order_by(text("applet_version"), FlowHistory.order, FlowItemHistory.order)
        )
        res = await session.execute(
            query,
            execution_options=immutabledict({"synchronize_session": False}),
        )
        data = res.all()

    cdn_client = await get_operations_bucket()
    key = cdn_client.generate_key(path_prefix, str(applet_id), PATH_FLOW_FILE_NAME)
    await save_csv(key, parse_obj_as(list[dict], data), cdn_client)


@app.command(
    short_help=f'Export applet "{APPLET_NAME or "NOT CONFIGURED"}"({APPLET_ID or "NOT CONFIGURED"})'
    f" flow data as csv file"
)
@coro
async def export_flows(
    applet_id: Optional[uuid.UUID] = typer.Option(None, "--applet_id", "-a"),
    path_prefix: Optional[str] = typer.Option(PATH_PREFIX, "--path-prefix", "-p"),
):
    """
    Create and upload to s3 csv file with flow data
    """
    assert path_prefix
    applet_id = get_applet_id(applet_id)
    print(f"Flow export start {applet_id}")
    tracemalloc.start()
    await _export_flows(applet_id, path_prefix)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print("Flow export finished")
    print("Peak memory usage:", peak)


##### Daily user flow schedule stuff
async def get_user_flow_events(
    session: AsyncSession, scheduled_date: datetime.date, applet_id: uuid.UUID
) -> list[FlowEventRawRow]:
    cte = (
        select(
            EventSchema.applet_id,
            EventSchema.id.label("event_id"),
            UserEventsSchema.user_id,
            FlowEventsSchema.flow_id,
            PeriodicitySchema.type.label("event_type"),
            case(
                (
                    PeriodicitySchema.type.in_(("WEEKDAYS", "DAILY")),
                    scheduled_date,
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
        .where(EventSchema.is_deleted == false(), PeriodicitySchema.type != PeriodicityType.ALWAYS)
    ).cte("user_flow_events")

    query = (
        select(
            AppletSchema.id.label("applet_id"),
            literal(scheduled_date, Date).label("date"),
            UserAppletAccessSchema.user_id.label("user_id"),
            SubjectSchema.secret_user_id.label("secret_user_id"),
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
        .join(
            SubjectSchema,
            and_(
                SubjectSchema.applet_id == UserAppletAccessSchema.applet_id,
                SubjectSchema.user_id == UserAppletAccessSchema.user_id,
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
            AppletSchema.id == applet_id,
            cte.c.event_id != null(),
            ActivityFlowSchema.is_hidden == false(),
        )
        .order_by(UserAppletAccessSchema.user_id, ActivityFlowSchema.name)
    )
    db_result = await session.execute(query)
    result = db_result.mappings().all()
    return parse_obj_as(list[FlowEventRawRow], result)


def filter_events(raw_events_rows: list[TRawRow], schedule_date: datetime.date) -> list[TRawRow]:  # noqa: C901
    filtered: list[TRawRow] = []
    for row in raw_events_rows:
        # TODO: patch events with periodicity WEEKDAYS, WEEKLY, some events don't have start_date and end_date
        # (the issue is in migrated data).
        # For current script is ok, because or applet does not have issues with WEEKDAYS, WEEKLY
        row.end_date = cast(datetime.date, row.end_date)
        row.start_date = cast(datetime.date, row.start_date)
        match row.event_type:
            case PeriodicityType.DAILY:
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                if schedule_date >= row.start_date and schedule_date <= row.end_date:
                    filtered.append(row)
            case PeriodicityType.ONCE:
                schedule_start_date = row.selected_date
                row.end_date = row.selected_date
                if row.is_crossday_event:
                    row.end_date += datetime.timedelta(days=1)
                if schedule_date >= schedule_start_date and schedule_date <= row.end_date:
                    filtered.append(row)
            case PeriodicityType.WEEKDAYS:
                last_weekday = FRIDAY_WEEKDAY
                if row.is_crossday_event:
                    last_weekday = SATURDAY_WEEKDAY
                    if row.end_date.weekday() == FRIDAY_WEEKDAY:
                        row.end_date += datetime.timedelta(days=1)
                if (
                    schedule_date.weekday() <= last_weekday
                    and schedule_date >= row.start_date
                    and schedule_date <= row.end_date
                ):
                    filtered.append(row)
            case PeriodicityType.WEEKLY:
                scheduled_weekday = row.start_date.weekday()
                following_weekday = scheduled_weekday
                if row.is_crossday_event:
                    # For crossday event need to check following day as well
                    following_weekday += 1
                    # If was SUNDAY start new week
                    if following_weekday > SUNDAY_WEEKDAY:
                        following_weekday = 0
                    # Increase end_date for crossday event only in case if weekdays of start and end days are equal.
                    # The same logic on frontend for schedule.
                    if row.start_date.weekday() == row.end_date.weekday():
                        row.end_date += datetime.timedelta(days=1)
                if (
                    (schedule_date.weekday() == scheduled_weekday or schedule_date.weekday() == following_weekday)
                    and schedule_date >= row.start_date
                    and schedule_date <= row.end_date
                ):
                    filtered.append(row)
            case PeriodicityType.MONTHLY:
                scheduled_monthday = row.start_date.day
                following_monthday = scheduled_monthday
                if row.is_crossday_event:
                    following_monthday += 1
                    if is_last_day_of_month(row.start_date):
                        following_monthday = 1
                    # Increase end_date only if start_date equal end_date
                    if (
                        is_last_day_of_month(row.start_date)
                        and is_last_day_of_month(row.end_date)
                        or row.start_date.day == row.end_date.day
                    ):
                        row.end_date += datetime.timedelta(days=1)
                if (
                    (
                        schedule_date.day == scheduled_monthday
                        or schedule_date.day == following_monthday
                        or (is_last_day_of_month(schedule_date) and row.start_date)
                    )
                    and schedule_date >= row.start_date
                    and schedule_date <= row.end_date
                ):
                    filtered.append(row)
    return filtered


@app.command(short_help="Export daily user flow schedule events to csv")
@coro
async def export_flow_schedule(
    run_date: datetime.datetime = typer.Argument(None, help="run date"),
    applet_id: Optional[uuid.UUID] = typer.Option(None, "--applet_id", "-a"),
    path_prefix: Optional[str] = typer.Option(PATH_PREFIX, "--path-prefix", "-p"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force run even if job executed before",
    ),
):
    assert path_prefix
    applet_id = get_applet_id(applet_id)
    scheduled_date = run_date.date() if run_date else datetime.date.today()

    job_name = f"export_flow_schedule_{applet_id}_{scheduled_date}"

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        owner_role = await UserAppletAccessCRUD(session).get_applet_owner(applet_id)
        owner_id = owner_role.user_id

        job_service = JobService(session, owner_id)
        async with atomic(session):
            try:
                job = await job_service.get_or_create_owned(
                    job_name, JobStatus.in_progress, accept_statuses=[JobStatus.error]
                )
            except JobStatusError as e:
                # prevent task execution if it's in progress or executed previously
                job = e.job
                if job.status == JobStatus.in_progress or not force:
                    raise
            if job.status != JobStatus.in_progress:
                await job_service.change_status(job.id, JobStatus.in_progress)

    print(f"Flow schedule export start {applet_id} ({scheduled_date})")
    tracemalloc.start()

    try:
        async with session_maker() as session:
            raw_data = await get_user_flow_events(session, scheduled_date, applet_id)
        print(f"Num raw rows is {len(raw_data)}")
        filtered = filter_events(raw_data, scheduled_date)
        print(f"Num filtered rows is {len(filtered)}")
        result = []
        for row in filtered:
            outrow = FlowEventOutputRow(
                applet_id=row.applet_id,
                date_prior_day=scheduled_date,
                user_id=row.user_id,
                secret_user_id=row.secret_user_id,
                flow_id=row.flow_id,
                flow_name=row.flow_name,
                applet_version=row.applet_version,
                scheduled_date=scheduled_date,
                schedule_start_time=row.schedule_start_time.strftime(OUTPUT_TIME_FORMAT),
                schedule_end_time=row.schedule_end_time.strftime(OUTPUT_TIME_FORMAT),
                event_id=row.event_id,
            ).dict()
            result.append(outrow)

        cdn_client = await get_operations_bucket()
        unique_prefix = f"{applet_id}/flow-schedule"

        prev_filename = PATH_USER_FLOW_SCHEDULE_FILE_NAME.format(date=scheduled_date - datetime.timedelta(days=1))
        prev_key = cdn_client.generate_key(path_prefix, unique_prefix, prev_filename)

        filename = PATH_USER_FLOW_SCHEDULE_FILE_NAME.format(date=scheduled_date)
        key = cdn_client.generate_key(path_prefix, unique_prefix, filename)

        path = settings.uploads_dir / filename

        with open(path, "wb") as f:
            try:
                cdn_client.download(prev_key, f)
            except ObjectNotFoundError:
                pass
            f.seek(0, io.SEEK_END)
            create_csv(result, append_to=f)
        with open(path, "rb") as f:
            print(f"Upload file to the {key}")
            await cdn_client.upload(key, f)

        os.remove(path)

        async with session_maker() as session:
            async with atomic(session):
                await JobService(session, owner_id).change_status(job.id, JobStatus.success)
    except Exception as e:
        async with session_maker() as session:
            async with atomic(session):
                await JobService(session, owner_id).change_status(job.id, JobStatus.error, {"error": str(e)})
        raise

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print("Flow schedule export finished")
    print("Peak memory usage:", peak)


##### Daily user activity schedule stuff
async def get_user_activity_events(
    session: AsyncSession, scheduled_date: datetime.date, applet_id: uuid.UUID
) -> list[ActivityEventRawRow]:
    cte = (
        select(
            EventSchema.applet_id,
            EventSchema.id.label("event_id"),
            UserEventsSchema.user_id,
            ActivityEventsSchema.activity_id,
            PeriodicitySchema.type.label("event_type"),
            case(
                (
                    PeriodicitySchema.type.in_(("WEEKDAYS", "DAILY")),
                    scheduled_date,
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
        .join(ActivityEventsSchema, ActivityEventsSchema.event_id == EventSchema.id)
        .where(EventSchema.is_deleted == false(), PeriodicitySchema.type != PeriodicityType.ALWAYS)
    ).cte("user_activity_events")

    query = (
        select(
            AppletSchema.id.label("applet_id"),
            literal(scheduled_date, Date).label("date"),
            UserAppletAccessSchema.user_id.label("user_id"),
            SubjectSchema.secret_user_id.label("secret_user_id"),
            ActivitySchema.id.label("activity_id"),
            ActivitySchema.name.label("activity_name"),
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
        .join(
            SubjectSchema,
            and_(
                SubjectSchema.applet_id == UserAppletAccessSchema.applet_id,
                SubjectSchema.user_id == UserAppletAccessSchema.user_id,
            ),
        )
        .join(ActivitySchema, ActivitySchema.applet_id == AppletSchema.id)
        .outerjoin(
            cte,
            and_(
                cte.c.applet_id == AppletSchema.id,
                cte.c.user_id == UserAppletAccessSchema.user_id,
                cte.c.activity_id == ActivitySchema.id,
            ),
        )
        .where(
            AppletSchema.id == applet_id,
            cte.c.event_id != null(),
            ActivitySchema.is_hidden == false(),
        )
        .order_by(UserAppletAccessSchema.user_id, ActivitySchema.name)
    )
    db_result = await session.execute(query)
    result = db_result.mappings().all()
    return parse_obj_as(list[ActivityEventRawRow], result)


@app.command(short_help="Export daily user activity schedule events to csv")
@coro
async def export_activity_schedule(
    run_date: datetime.datetime = typer.Argument(None, help="run date"),
    applet_id: Optional[uuid.UUID] = typer.Option(None, "--applet_id", "-a"),
    path_prefix: Optional[str] = typer.Option(PATH_PREFIX, "--path-prefix", "-p"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force run even if job executed before",
    ),
):
    assert path_prefix
    applet_id = get_applet_id(applet_id)
    scheduled_date = run_date.date() if run_date else datetime.date.today()

    job_name = f"export_activity_schedule_{applet_id}_{scheduled_date}"

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        owner_role = await UserAppletAccessCRUD(session).get_applet_owner(applet_id)
        owner_id = owner_role.user_id

        job_service = JobService(session, owner_id)
        async with atomic(session):
            try:
                job = await job_service.get_or_create_owned(
                    job_name, JobStatus.in_progress, accept_statuses=[JobStatus.error]
                )
            except JobStatusError as e:
                # prevent task execution if it's in progress or executed previously
                job = e.job
                if job.status == JobStatus.in_progress or not force:
                    raise
            if job.status != JobStatus.in_progress:
                await job_service.change_status(job.id, JobStatus.in_progress)
    print(f"Activity schedule export start {applet_id} ({scheduled_date})")
    tracemalloc.start()

    try:
        session_maker = session_manager.get_session()
        async with session_maker() as session:
            raw_data = await get_user_activity_events(session, scheduled_date, applet_id)
        print(f"Num raw rows is {len(raw_data)}")
        filtered = filter_events(raw_data, scheduled_date)
        print(f"Num filtered rows is {len(filtered)}")
        result = []
        for row in filtered:
            outrow = ActivityEventOutputRow(
                applet_id=row.applet_id,
                date_prior_day=scheduled_date,
                user_id=row.user_id,
                secret_user_id=row.secret_user_id,
                activity_id=row.activity_id,
                activity_name=row.activity_name,
                applet_version=row.applet_version,
                scheduled_date=scheduled_date,
                schedule_start_time=row.schedule_start_time.strftime(OUTPUT_TIME_FORMAT),
                schedule_end_time=row.schedule_end_time.strftime(OUTPUT_TIME_FORMAT),
                event_id=row.event_id,
            ).dict()
            result.append(outrow)

        cdn_client = await get_operations_bucket()
        unique_prefix = f"{applet_id}/activity-schedule"

        prev_filename = PATH_USER_ACTIVITY_SCHEDULE_FILE_NAME.format(date=scheduled_date - datetime.timedelta(days=1))
        prev_key = cdn_client.generate_key(path_prefix, unique_prefix, prev_filename)

        filename = PATH_USER_ACTIVITY_SCHEDULE_FILE_NAME.format(date=scheduled_date)
        key = cdn_client.generate_key(path_prefix, unique_prefix, filename)

        path = settings.uploads_dir / filename

        with open(path, "wb") as f:
            try:
                cdn_client.download(prev_key, f)
            except ObjectNotFoundError:
                pass
            f.seek(0, io.SEEK_END)
            create_csv(result, append_to=f)
        with open(path, "rb") as f:
            print(f"Upload file to the {key}")
            await cdn_client.upload(key, f)

        os.remove(path)
        async with session_maker() as session:
            async with atomic(session):
                await JobService(session, owner_id).change_status(job.id, JobStatus.success)
    except Exception as e:
        async with session_maker() as session:
            async with atomic(session):
                await JobService(session, owner_id).change_status(job.id, JobStatus.error, {"error": str(e)})
        raise

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print("Activity schedule export finished")
    print("Peak memory usage:", peak)
