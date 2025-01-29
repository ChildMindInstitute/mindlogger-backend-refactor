import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.activities.db.schemas.activity import ActivitySchema
from apps.schedule.service import ScheduleService
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer()


async def get_assessments(session: AsyncSession) -> list[ActivitySchema]:
    query: Query = select(ActivitySchema)
    query = query.where(ActivitySchema.is_reviewable.is_(True))
    res = await session.execute(query)
    return res.scalars().all()  # noqa


@app.command(short_help="Remove events for assessments")
@coro
async def remove_events():
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        async with atomic(session):
            try:
                assessments = await get_assessments(session)
                service = ScheduleService(session)
                for activity in assessments:
                    print(f"Applet: {activity.applet_id} Activity: {activity.id}")
                    await service.delete_by_activity_ids(activity.applet_id, [activity.id])
            except Exception as ex:
                print(ex)
