import asyncio
import datetime

from bson.objectid import ObjectId

from apps.migrate.exception.exception import (
    FormatldException,
    EmptyAppletException,
)
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
    toSkip = [
        "63bd5736aba6fd499bda0fee",  # subscales refer to name (question: Put your name)
        # "63be5c97aba6fd499bda1960",  # Totalscoretable incorrect raw score '~10~0' - fixed
        "63be9739aba6fd499bda1eea",  # subscale refer to text item, instead of single,multi, slider
        "63c00872aba6fd499bda2990",  # subscale refer to text item, instead of single,multi, slider
        "63be9916aba6fd499bda1fd5",  # incorrect github url
        "63be6ce5aba6fd499bda1b43",  # js expression error TODO check jsexpression and whole doc
        "63bd5734aba6fd499bda0fe3",  # flow has activity that is being duplicated from another applet.
        "63c52d2aaba6fd499bda35e1",  # converter not parsing score conditions
        "63e4efd41d3f3e0f89b488bd",  # wrong context file in activity for 2-version
        "63f722ed1d3f3e0f89b488d8",  # applet name duplicates
    ]
    # applets = Applet().find(
    #     query={"_id": ObjectId("63be5c97aba6fd499bda1960")}, fields={"_id": 1}
    # )
    # applets = Applet().find(query={'_id': ObjectId('64d0de7e5e3d9e04c28a1720')}, fields={"_id": 1}) # TODO: 6.2.6 6.2.7 ???
    # applets = Applet().find(query={'_id': ObjectId('62d15a03154fa87efa129760')}, fields={"_id": 1})
    applets = Applet().find(
        query={
            "meta.applet.displayName": {"$exists": True},
            "meta.applet.deleted": {"$ne": True},
            "meta.applet.editing": {"$ne": True},
            "created": {"$gte": datetime.datetime(2023, 1, 1, 0, 0, 0, 0)},
        },
        fields={"_id": 1},
    )
    skipUntil = "6411c4dbeddaf60f21c3a04c"
    appletsCount = applets.count()
    print("total", appletsCount)
    for index, applet_id in enumerate(applets, start=1):
        applet_id = str(applet_id["_id"])
        if skipUntil == applet_id:
            skipUntil = None
        if skipUntil is not None or applet_id in toSkip:
            continue
        print("processing", applet_id, index, "/", appletsCount)
        try:
            applet: dict | None = await mongo.get_applet(
                applet_id
            )  # noqa: F841

            applets, owner_id = await mongo.get_applet_versions(applet_id)
            for version, _applet in applets.items():
                _applet.extra_fields["created"] = applet.extra_fields[
                    "created"
                ]

            if applets != {}:
                applets[list(applets.keys())[-1]] = applet
            else:
                applets[applet.extra_fields["version"]] = applet

            await postgres.save_applets(applets, owner_id)
        except (FormatldException, EmptyAppletException) as e:
            print("Skipped because: ", e.message)


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
