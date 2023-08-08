import asyncio
from bson.objectid import ObjectId

from apps.migrate.services.mongo import Mongo
from apps.migrate.services.postgres import Postgres
from apps.girderformindlogger.models.applet import Applet


# class Convertor:
#     @staticmethod
#     def conver_users(users: list[dict]) -> list[dict]:
#         """Convert user from mongo into user
#         that can be stored into the Postgres"""
#         pass


async def migrate_applets(mongo: Mongo, postgres: Postgres):
    applets = Applet().find(
        query={"_id": ObjectId("6493172ee828ce3fa02a5b43")}, fields={"_id": 1}
    )
    # applets = Applet().find(query={'_id': ObjectId('64d0de7e5e3d9e04c28a1720')}, fields={"_id": 1}) # TODO: 6.2.6 6.2.7 ???
    # applets = Applet().find(query={'_id': ObjectId('62d15a03154fa87efa129760')}, fields={"_id": 1})
    # applets = Applet().find(query={'meta.applet': {'$exists': True}}, fields={"_id": 1})
    skipUntil = None  # ObjectId('62d15a03154fa87efa129760')
    appletsCount = applets.count()
    print("total", appletsCount)
    for index, applet_id in enumerate(applets, start=1):
        applet_id = str(applet_id["_id"])
        if skipUntil == applet_id:
            skipUntil = None
        if skipUntil is not None:
            continue
        print("processing", applet_id, index, "/", appletsCount)

        applet: dict = await mongo.get_applet(applet_id)  # noqa: F841

        applets, owner_id = await mongo.get_applet_versions(applet_id)
        for version, _applet in applets.items():
            _applet.extra_fields["created"] = applet.extra_fields["created"]

        applets[list(applets.keys())[-1]] = applet
        await postgres.save_applets(applets, owner_id)


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
    await migrate_applets(mongo, postgres)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
