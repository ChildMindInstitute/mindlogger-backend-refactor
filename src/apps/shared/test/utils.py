from sqlalchemy import text

from infrastructure.database import Base
from infrastructure.database.core import session_manager


async def truncate_tables():
    AsyncSession = session_manager.get_session()
    async with AsyncSession() as session:
        for table_name in Base.metadata.tables:
            if table_name in (
                "users",
                "user_devices",
                "applets",
                "user_applet_accesses",
                "applet_histories",
                "activities",
                "activity_items",
                "activity_histories",
                "activity_item_histories",
                "flows",
                "flow_items",
                "flow_histories",
                "flow_item_histories",
            ):
                continue
            elif table_name == "users_workspaces":
                query = text(f"delete from {table_name} where user_id != '57b63dfa-5cee-4a53-a69e-0a35407e601d'")
            elif table_name == "themes":
                query = text("delete from themes where is_default = false")
            else:
                query = text(f"""TRUNCATE "{table_name}" CASCADE""")
            await session.execute(query)
        await session.commit()
