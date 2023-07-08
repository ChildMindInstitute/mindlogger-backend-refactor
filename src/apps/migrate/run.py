import asyncio

from apps.migrate.services.mongo import Mongo
from apps.migrate.services.postgres import Postgres


# class Convertor:
#     @staticmethod
#     def conver_users(users: list[dict]) -> list[dict]:
#         """Convert user from mongo into user
#         that can be stored into the Postgres"""
#         pass


def foo(item, key):
    return item()


async def main():
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    # users: list[dict] = mongo.get_users()
    # users_mapping = postgres.save_users(users)

    # Migrate with users_workspace
    # postgres.save_users_workspace(users_mapping)

    # applets = mongo.get_applets()

    # TODO: Migrate with applets
    applets: list[dict] = await mongo.get_applets()

    await postgres.save_applets(applets)

    # TODO: Migrate with activities
    # activities: list[dict] = mongo.get_activities()
    # new_activities_mapping: dict[str, dict] = postgres.save_activities(
    #     activities
    # )

    # TODO: Migrate with activity items
    # items: list[dict] = mongo.get_items()
    # created_items = postgres.save_activity_items(
    #     items, new_activities_mapping
    # )

    breakpoint()

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
