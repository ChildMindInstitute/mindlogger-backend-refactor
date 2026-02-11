from sqlalchemy import text

from infrastructure.database import Base
from infrastructure.database.core import session_manager


async def truncate_tables():
    AsyncSession = session_manager.get_session()
    async with AsyncSession() as session:
        for table_name in Base.metadata.tables:
            if table_name == "users_workspaces":
                query = text(f"delete from {table_name} where user_id != '57b63dfa-5cee-4a53-a69e-0a35407e601d'")
                await session.execute(query)
            elif table_name == "themes":
                query = text("delete from themes where is_default = false")
                await session.execute(query)
            elif table_name in (
                "alerts",
                "cart",
                "folder_applets",
                "folders",
                "invitations",
                "library",
                "notification_logs",
                "reusable_item_choices",
                "token_blacklist",
                "transfer_ownership",
                "user_pins",
            ):
                query = text(f"""TRUNCATE "{table_name}" CASCADE""")
                await session.execute(query)
        await session.commit()
