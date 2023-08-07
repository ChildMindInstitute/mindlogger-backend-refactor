import asyncio

from apps.migrate.services.mongo import Mongo
from apps.migrate.services.postgres import Postgres

# class Convertor:
#     @staticmethod
#     def conver_users(users: list[dict]) -> list[dict]:
#         """Convert user from mongo into user
#         that can be stored into the Postgres"""
#         pass


async def main():
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    # users: list[dict] = mongo.get_users()
    # users_mapping = postgres.save_users(users)
    # Migrate with users_workspace
    # workspaces = mongo.get_users_workspaces(list(users_mapping.keys()))
    # postgres.save_users_workspace(workspaces, users_mapping)

    # Migrate applets, activities, items

    applet: dict = await mongo.get_applet(
        "62d15a03154fa87efa129760"
    )  # noqa: F841

    applets, owner_id = await mongo.get_applet_versions(
        "62d15a03154fa87efa129760"
    )
    await postgres.save_applets(applets, owner_id, applet)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
