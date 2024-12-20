from rich import print
from sqlalchemy.ext.asyncio import AsyncSession

SQL_ALERT_DEFAULT_TYPE = """
    update alerts
    set type='answer'
    where type is null;
"""


async def main(session: AsyncSession, *args, **kwargs):
    print("Execute:")
    print(SQL_ALERT_DEFAULT_TYPE)
    await session.execute(SQL_ALERT_DEFAULT_TYPE)
    print("Done")
