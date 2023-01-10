from sqlalchemy import text

from infrastructure.database import Base, session_manager


async def update_sequence():
    session = session_manager.get_session()
    for name, table in Base.metadata.tables.items():
        if not table.c.id.autoincrement:
            continue
        query = text(
            f"""
        SELECT SETVAL('{name}_id_seq',
            (SELECT COALESCE(MAX(id), 0) FROM "{name}") + 1, false)
        """
        )
        await session.execute(query)
    await session.commit()


async def truncate_tables():
    session = session_manager.get_session()
    for name, table in Base.metadata.tables.items():
        query = text(f"""TRUNCATE "{name}" CASCADE""")
        await session.execute(query)
    await session.commit()
