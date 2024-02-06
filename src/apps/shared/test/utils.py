from sqlalchemy import text

from infrastructure.database import Base, session_manager


async def truncate_tables():
    Session = session_manager.get_session()
    async with Session() as session:
        for table_name in Base.metadata.tables:
            if table_name in ("users", "user_devices"):
                continue
            elif table_name == "users_workspaces":
                query = text(f"delete from {table_name} where user_id != '57b63dfa-5cee-4a53-a69e-0a35407e601d'")
            else:
                query = text(f"""TRUNCATE "{table_name}" CASCADE""")
            await session.execute(query)
        await session.commit()
