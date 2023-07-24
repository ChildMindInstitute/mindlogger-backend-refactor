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

    # applets: list[dict] = await mongo.get_applets()  # noqa: F841

    applets = await mongo.get_applet_versions()  # noqa: F841
    # await postgres.save_applets(applets)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
