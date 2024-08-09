# patches/m2_7285_set_auto_assign.py

from sqlalchemy.ext.asyncio import AsyncSession

# SQL Queries
SET_DEFAULT_AUTO_ASSIGN_ACTIVITIES_SQL = """
    ALTER TABLE activities ALTER COLUMN auto_assign SET DEFAULT true;
"""

SET_DEFAULT_AUTO_ASSIGN_FLOWS_SQL = """
    ALTER TABLE flows ALTER COLUMN auto_assign SET DEFAULT true;
"""

UPDATE_EXISTING_ACTIVITIES_SQL = """
    UPDATE activities SET auto_assign = true WHERE auto_assign IS NULL;
"""

UPDATE_EXISTING_FLOWS_SQL = """
    UPDATE flows SET auto_assign = true WHERE auto_assign IS NULL;
"""

async def main(session: AsyncSession, *args, **kwargs):
    try:
        # Set the default value of auto_assign to true for new records
        await session.execute(SET_DEFAULT_AUTO_ASSIGN_ACTIVITIES_SQL)
        await session.execute(SET_DEFAULT_AUTO_ASSIGN_FLOWS_SQL)

        # Update existing records to set auto_assign to true
        await session.execute(UPDATE_EXISTING_ACTIVITIES_SQL)
        await session.execute(UPDATE_EXISTING_FLOWS_SQL)

        # Commit the transaction
        await session.commit()
    except Exception as ex:
        # Rollback the transaction in case of error
        await session.rollback()
        raise ex
