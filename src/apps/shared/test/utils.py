from sqlalchemy import Integer, text

from infrastructure.database import Base, session_manager


async def update_sequence():
    session = session_manager.get_session()
    for name, table in Base.metadata.tables.items():
        for primary_key in table.primary_key.columns:
            if not isinstance(primary_key.type, Integer):
                continue
            if primary_key.autoincrement not in ("auto", True):
                continue
            query = text(
                f"""
            SELECT SETVAL('{name}_{primary_key.name}_seq',
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
