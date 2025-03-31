import os
import uuid
from uuid import UUID

from sqlalchemy import cast, desc, func, select, update
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
    ActivityItemSchema,
    ActivitySchema,
)

# Note: You can use environment variables to overwrite default values.
# AGE_SCREEN_QUESTION_TRANSLATION to update the question value for the age screen.
# GENDER_SCREEN_QUESTION_TRANSLATION to update the question value for the gender screen.
# GENDER_SCREEN_RESPONSE_MALE_TRANSLATION to update the response value for the male option.
# GENDER_SCREEN_RESPONSE_FEMALE_TRANSLATION to update the response value for the female option.


async def update_age_screen(session: AsyncSession, applet_id: UUID):
    print(f"Updating age screen for applet_id: {applet_id}")

    new_question_value = os.environ.get("AGE_SCREEN_QUESTION_TRANSLATION", "Ηλικία:")

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
                cast(new_question_value, JSONB),
                True,
            )
        )
    )

    await session.execute(update_query, execution_options=immutabledict({"synchronize_session": "fetch"}))

    query = select(ActivityItemSchema.activity_id).where(
        ActivityItemSchema.name == "age_screen",
        ActivityItemSchema.activity_id.in_(select(ActivitySchema.id).where(ActivitySchema.applet_id == applet_id)),
    )

    res = await session.execute(query)

    for item in res.mappings().all():
        print(f"Updating activity id: {item.activity_id}")

        # Determine the current version of the activity_id
        subquery = (
            select(ActivityHistorySchema.id_version)
            .where(ActivityHistorySchema.id == item.activity_id)
            .order_by(desc(ActivityHistorySchema.updated_at))
            .limit(1)
        )

        current_version_activity_id = await session.execute(subquery)
        current_version_activity_id = current_version_activity_id.scalar()

        print("Current activity version id: ", current_version_activity_id)

        # Update the ActivityItemHistorySchema table
        update_history_query = (
            update(ActivityItemHistorySchema)
            .where(
                ActivityItemHistorySchema.name == "age_screen",
                ActivityItemHistorySchema.activity_id == current_version_activity_id,
            )
            .values(
                question=func.jsonb_set(
                    ActivityItemHistorySchema.question,
                    ["en"],
                    cast(new_question_value, JSONB),
                    True,
                )
            )
        )

        await session.execute(update_history_query, execution_options=immutabledict({"synchronize_session": "fetch"}))

    print(f"Updated age screen for applet_id: {applet_id}")


async def update_gender_screen(session: AsyncSession, applet_id: UUID):
    print(f"Updating gender screen for applet_id: {applet_id}")
    new_question_value = os.environ.get("GENDER_SCREEN_QUESTION_TRANSLATION", "Φύλο:")

    translations = {
        "Male": os.environ.get("GENDER_SCREEN_RESPONSE_MALE_TRANSLATION", "Άντρας"),
        "Female": os.environ.get("GENDER_SCREEN_RESPONSE_FEMALE_TRANSLATION", "Γυναίκα"),
    }

    query = select(ActivityItemSchema.id, ActivityItemSchema.response_values, ActivityItemSchema.activity_id).where(
        ActivityItemSchema.name == "gender_screen",
        ActivityItemSchema.activity_id.in_(select(ActivitySchema.id).where(ActivitySchema.applet_id == applet_id)),
    )

    res = await session.execute(query)

    for item in res.mappings().all():
        print(f"Updating item id: {item.id}")

        # Checking for male/female index response_values, even for already translated items,
        # this will make sure this script always update items to new translations
        male_index = next(
            (
                index
                for (index, option) in enumerate(item.response_values["options"])
                if option["value"] == 0  # male option will always have value 0
            ),
            -1,
        )

        female_index = next(
            (
                index
                for (index, option) in enumerate(item.response_values["options"])
                if option["value"] == 1  # female option will always have value 1
            ),
            -1,
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
                    cast(new_question_value, JSONB),
                    True,
                ),
                response_values=update_response_values,
            )
        )

        await session.execute(update_query, execution_options=immutabledict({"synchronize_session": "fetch"}))

        # Determine the current version of the activity_id
        subquery = (
            select(ActivityHistorySchema.id_version)
            .where(ActivityHistorySchema.id == item.activity_id)
            .order_by(desc(ActivityHistorySchema.updated_at))
            .limit(1)
        )

        current_version_activity_id = await session.execute(subquery)
        current_version_activity_id = current_version_activity_id.scalar()

        print("Current activity version id: ", current_version_activity_id)

        # Update the ActivityItemHistorySchema table
        update_history_response_values = func.jsonb_set(
            func.jsonb_set(
                ActivityItemHistorySchema.response_values,
                ["options", str(male_index), "text"],
                cast(translations["Male"], JSONB),
                True,
            ),
            ["options", str(female_index), "text"],
            cast(translations["Female"], JSONB),
            True,
        )

        update_history_query = (
            update(ActivityItemHistorySchema)
            .where(
                ActivityItemHistorySchema.name == "gender_screen",
                ActivityItemHistorySchema.activity_id == current_version_activity_id,
            )
            .values(
                question=func.jsonb_set(
                    ActivityItemHistorySchema.question,
                    ["en"],
                    cast(new_question_value, JSONB),
                    True,
                ),
                response_values=update_history_response_values,
            )
        )

        await session.execute(update_history_query, execution_options=immutabledict({"synchronize_session": "fetch"}))

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
