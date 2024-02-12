from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import Base


async def truncate_tables(global_session: AsyncSession):
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
        await global_session.execute(query)
    await global_session.commit()
