from sqlalchemy.ext.asyncio import AsyncSession

# SQL Queries to update existing records
UPDATE_EXISTING_ACTIVITIES_SQL = """
    UPDATE activities SET auto_assign = true WHERE auto_assign IS NULL;
"""

UPDATE_EXISTING_FLOWS_SQL = """
    UPDATE flows SET auto_assign = true WHERE auto_assign IS NULL;
"""


async def main(session: AsyncSession, *args, **kwargs):
    try:
        # Update existing records to set auto_assign to true
        await session.execute(UPDATE_EXISTING_ACTIVITIES_SQL)
        await session.execute(UPDATE_EXISTING_FLOWS_SQL)

        # Commit the transaction
        await session.commit()
    except Exception as ex:
        # Rollback the transaction in case of error
        await session.rollback()
        raise ex
