import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema
from apps.activities.domain.response_type_config import ResponseType


async def main(session: AsyncSession, *args, **kwargs):
    query: Query = select(ActivityItemSchema)
    query = query.join(
        ActivitySchema, ActivityItemSchema.activity_id == ActivitySchema.id
    )
    query = query.where(
        ActivitySchema.applet_id
        == uuid.UUID("62d06045-acd3-5a10-54f1-06f600000000")
    )
    query = query.where(
        ActivityItemSchema.response_type == ResponseType.SLIDER
    )
    res = await session.execute(query)
    slider_items: list[ActivityItemSchema] = res.scalars().all()
    for item in slider_items:
        item.config["show_tick_marks"] = True
        item.config["show_tick_labels"] = True

        await session.execute(
            update(ActivityItemSchema)
            .where(ActivityItemSchema.id == item.id)
            .values(config=item.config)
        )
