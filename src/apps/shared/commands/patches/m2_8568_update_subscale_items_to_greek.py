import uuid
from uuid import UUID

from sqlalchemy import cast, func, select, update
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.db.schemas import ActivityItemSchema, ActivitySchema


async def update_age_screen(session: AsyncSession, applet_id: UUID):
    print(f"Updating age screen for applet_id: {applet_id}")

    new_question_value = {"el": "Πόσων χρονών είστε;"}

    update_query = (
        update(ActivityItemSchema)
        .where(
            ActivityItemSchema.name == "age_screen",
            ActivityItemSchema.activity_id.in_(select(ActivitySchema.id).where(ActivitySchema.applet_id == applet_id)),
        )
        .values(
            question=func.jsonb_set(
                ActivityItemSchema.question,
                ["en"],
                cast(new_question_value["el"], JSONB),
                True,
            )
        )
    )

    await session.execute(update_query, execution_options=immutabledict({"synchronize_session": "fetch"}))
    print(f"Updated age screen for applet_id: {applet_id}")


async def update_gender_screen(session: AsyncSession, applet_id: UUID):
    print(f"Updating gender screen for applet_id: {applet_id}")
    new_question_value = {"el": "Ποιο φύλο σας αποδόθηκε κατά την γέννησή σας;"}

    translations = {
        "Male": "Ανδρας",
        "Female": "Γυναίκα",
    }

    query = select(ActivityItemSchema.id, ActivityItemSchema.response_values).where(
        ActivityItemSchema.name == "gender_screen",
        ActivityItemSchema.activity_id.in_(select(ActivitySchema.id).where(ActivitySchema.applet_id == applet_id)),
    )

    res = await session.execute(query)

    for item in res.mappings().all():
        print(f"Updating item id: {item.id}")

        male_index = next(
            (index for (index, option) in enumerate(item.response_values["options"]) if option["text"] == "Male"), -1
        )

        female_index = next(
            (index for (index, option) in enumerate(item.response_values["options"]) if option["text"] == "Female"), -1
        )

        if (male_index == -1) or (female_index == -1):
            continue

        update_response_values = func.jsonb_set(
            func.jsonb_set(
                ActivityItemSchema.response_values,
                ["options", str(male_index), "text"],
                cast(translations["Male"], JSONB),
                True,
            ),
            ["options", str(female_index), "text"],
            cast(translations["Female"], JSONB),
            True,
        )

        update_query = (
            update(ActivityItemSchema)
            .where(
                ActivityItemSchema.name == "gender_screen",
                ActivityItemSchema.id == item.id,
            )
            .values(
                question=func.jsonb_set(
                    ActivityItemSchema.question,
                    ["en"],
                    cast(new_question_value["el"], JSONB),
                    True,
                ),
                response_values=update_response_values,
            )
        )

        await session.execute(update_query, execution_options=immutabledict({"synchronize_session": "fetch"}))
    print(f"Updated gender screen for applet_id: {applet_id}")


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    applet_id: uuid.UUID | None = None,
    *args,
    **kwargs,
):
    if applet_id is None:
        return

    print(f"Updating subscale items to Greek for applet_id: {applet_id}")

    await update_age_screen(session, applet_id)
    await update_gender_screen(session, applet_id)

    return
