from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityItemSchema
from apps.activities.domain.response_type_config import ResponseType


async def main(session: AsyncSession, *args, **kwargs):
    query: Query = select(ActivityItemSchema)
    query = query.where(ActivityItemSchema.response_type == ResponseType.SINGLESELECT)
    query = query.where(
        ActivityItemSchema.config["auto_advance"] == None  # noqa : E711
    )
    res = await session.execute(query)
    single_select_items: list[ActivityItemSchema] = res.scalars().all()
    for item in single_select_items:
        item.config["auto_advance"] = True

        await session.execute(
            update(ActivityItemSchema).where(ActivityItemSchema.id == item.id).values(config=item.config)
        )
