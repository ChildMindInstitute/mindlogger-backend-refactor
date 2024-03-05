import asyncio
import codecs
import csv
import io
import tracemalloc
from functools import wraps

import typer
from pydantic import parse_obj_as
from rich import print
from sqlalchemy import func, select, text
from sqlalchemy.cimmutabledict import immutabledict

from apps.activities.db.schemas import ActivityHistorySchema as ActivityHistory
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema as FlowHistory
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema as FlowItemHistory
from infrastructure.database import session_manager
from infrastructure.dependency.cdn import get_operations_bucket
from infrastructure.utility import CDNClient

app = typer.Typer()


APPLET_ID = "64c975a4-22d8-180c-f9b3-e42600000000"
APPLET_NAME = "Revised NIMH EMA"
PATH_PREFIX = "export-ami"
PATH_FLOW_FILE_NAME = "flow-items.csv"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def save_csv(path: str, data: list[dict], cdn_client: CDNClient, columns: list | None = None):
    if data:
        if not columns:
            columns = list(data[0].keys())

        fin = io.BytesIO()
        StreamWriter = codecs.getwriter("utf-8")
        f_wrapper = StreamWriter(fin)

        writer = csv.DictWriter(f_wrapper, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        fin.seek(0)
        await cdn_client.upload(path, fin)


async def _flows_export():
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
            .where(FlowHistory.applet_id.like(f"{APPLET_ID}_%"))
            .order_by(text("applet_version"), FlowHistory.order, FlowItemHistory.order)
        )
        res = await session.execute(
            query,
            execution_options=immutabledict({"synchronize_session": False}),
        )
        data = res.all()

    cdn_client = await get_operations_bucket()
    path = cdn_client.generate_key(PATH_PREFIX, str(APPLET_ID), PATH_FLOW_FILE_NAME)
    await save_csv(path, parse_obj_as(list[dict], data), cdn_client)


@app.command(short_help=f'Export applet "{APPLET_NAME}"({APPLET_ID}) flow data as csv file')
@coro
async def flows_export_ema():
    """
    Create and upload to s3 csv file with flow data
    """
    print("Flow export start")
    tracemalloc.start()
    await _flows_export()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print("Flow export finished")
    print("Peak memory usage:", peak)
