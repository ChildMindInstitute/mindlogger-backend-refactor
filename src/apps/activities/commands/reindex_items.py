import asyncio
import uuid
from functools import wraps

import typer
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_full import ActivityFull
from apps.activities.domain.response_values import (
    MultiSelectionValues,
    SingleSelectionValues,
)
from apps.activity_flows.domain.flow_update import (
    ActivityFlowItemUpdate,
    FlowUpdate,
)
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from infrastructure.database import atomic, session_manager

app = typer.Typer()


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def print_results(applets: list[tuple[uuid.UUID, str]]):
    table = Table(
        show_header=True,
        title="Fixed applets",
        title_style=Style(bold=True),
    )
    table.add_column("#")
    table.add_column("id")
    table.add_column("display name")
    i = 1
    for applet in applets:
        table.add_row(str(i), str(applet[0]), applet[1])
        i += 1
    print(table)


async def get_applets_with_problem(session: AsyncSession) -> list[uuid.UUID]:
    sql = text(
        """
        with broken_activity_ids as (
            select distinct activity_id as id
            from activity_items
            where exists (
                select 1
                from
                    jsonb_array_elements(response_values->'options') as opt1,
                    jsonb_array_elements(response_values->'options') as opt2
                where opt1->>'value' = opt2->>'value'
                and opt1->>'id' <> opt2->>'id'
            )
        )
        select a.applet_id
        from broken_activity_ids ba
        join activities a on ba.id = a.id
    """
    )
    result = await session.execute(sql)
    return result.scalars().all()


async def is_need_to_override(
    values: SingleSelectionValues | MultiSelectionValues,
) -> bool:
    unique_count = len(set(map(lambda v: v.value, values.options)))
    return unique_count != len(values.options)


async def override_indexes(
    values: SingleSelectionValues | MultiSelectionValues,
) -> SingleSelectionValues | MultiSelectionValues:
    for i in range(len(values.options)):
        values.options[i].value = i
    return values


async def _reindex_items(activities: list[ActivityFull]) -> list[ActivityFull]:
    for activity in activities:
        for item in activity.items:
            if isinstance(
                item.response_values, SingleSelectionValues
            ) or isinstance(item.response_values, MultiSelectionValues):
                fix = await is_need_to_override(item.response_values)
                if fix:
                    item.response_values = await override_indexes(
                        item.response_values
                    )
    return activities


async def reindex_applet(
    session: AsyncSession, applet_id: uuid.UUID
) -> AppletFull:
    fake_user_id = uuid.uuid4()
    applet = await AppletService(session, fake_user_id).get_full_applet(
        applet_id
    )
    role = await UserAppletAccessCRUD(session).get_applet_owner(applet_id)
    fixed_activities = await _reindex_items(applet.activities)
    activity_flows = []
    for flow in applet.activity_flows:
        items = []
        for flow_item in flow.items:
            activity = next(
                filter(
                    lambda a: a.id == flow_item.activity_id, fixed_activities
                ),
                None,
            )
            if not activity:
                raise Exception(f"Activity {flow_item.activity_id} not found")
            item = ActivityFlowItemUpdate(
                id=flow_item.id, activity_key=activity.key
            )
            items.append(item)
        flow_update = FlowUpdate(
            id=flow.id,
            name=flow.name,
            description=flow.description,
            is_single_report=flow.is_single_report,
            hide_badge=flow.hide_badge,
            report_included_activity_name=flow.report_included_activity_name,
            report_included_item_name=flow.report_included_item_name,
            is_hidden=flow.is_hidden,
            items=items,
        )
        activity_flows.append(flow_update)
    update_values = AppletUpdate(
        display_name=applet.display_name,
        description=applet.description,
        about=applet.about,
        image=applet.image,
        watermark=applet.watermark,
        theme_id=applet.theme_id,
        link=applet.link,
        require_login=applet.require_login,
        pinned_at=applet.pinned_at,
        retention_period=applet.retention_period,
        retention_type=applet.retention_type,
        stream_enabled=applet.stream_enabled,
        encryption=applet.encryption,
        activities=fixed_activities,
        activity_flows=activity_flows,
    )
    async with atomic(session):
        await AppletService(session, role.owner_id).update(
            applet.id, update_values
        )
    return applet


@app.command(short_help="Find and fix activity_items automatically")
@coro
async def reindex_auto():
    s_maker = session_manager.get_session()
    try:
        async with s_maker() as session:
            result = []
            applet_ids = await get_applets_with_problem(session)
            count_all = len(applet_ids)
            count = 0
            for applet_id in applet_ids:
                count += 1
                print(f"Processing {count}/{count_all}")
                applet = await reindex_applet(session, applet_id)
                result.append(
                    (
                        applet.id,
                        applet.display_name,
                    )
                )
            print_results(result)
    except Exception as ex:
        print(f"[bold red] {ex}")


@app.command(short_help="Fix indexation of activity items")
@coro
async def reindex(
    applet_id: uuid.UUID = typer.Argument(..., help="Applet id"),
):
    s_maker = session_manager.get_session()
    try:
        async with s_maker() as session:
            applet = await reindex_applet(session, applet_id)
            print_results(
                [
                    (
                        applet.id,
                        applet.display_name,
                    )
                ]
            )
    except Exception as ex:
        print(f"[bold red] {ex}")
