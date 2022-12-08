from sqlalchemy import text

from infrastructure.database import session_manager
from src.infrastructure.database import Base


async def update_sequence():
    session = session_manager.get_session()
    for name, table in Base.metadata.tables.items():
        if not table.c.id.autoincrement:
            continue
        query = text(
            f"""SELECT SETVAL('{name}_id_seq', (SELECT COALESCE(MAX(id), 1) FROM "{name}"))"""
        )
        await session.execute(query)
    await session.commit()


async def truncate_tables():
    session = session_manager.get_session()
    for name, table in Base.metadata.tables.items():
        query = text(f"""TRUNCATE "{name}" CASCADE""")
        await session.execute(query)
    await session.commit()
