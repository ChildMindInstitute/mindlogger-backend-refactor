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
from apps.girderformindlogger.models.item import Item


async def migrate_applets(mongo: Mongo, postgres: Postgres):
    toSkip = [
        "5fd26d9dc47c585b7c7334fa",  # activity items doesnt exist
        "60ddb7645fa6a85768b6621d",  # activity item doesnt exist
        "61dda2b2025fb7a0d647959a",  # broken context age repronim
    ]
    # applets = Applet().find(
    #     query={"_id": ObjectId("63be5c97aba6fd499bda1960")}, fields={"_id": 1}
    # )
    # applets = Applet().find(query={'_id': ObjectId('64d0de7e5e3d9e04c28a1720')}, fields={"_id": 1}) # TODO: 6.2.6 6.2.7 ???

    # applets = Applet().find(
    #     query={"_id": ObjectId("5fa5a276bdec546ce77b298b")}, fields={"_id": 1}
    # )

    # answers = Item().find(
    #     query={
    #         "meta.dataSource": {"$exists": True},
    #         "created": {
    #             "$gte": datetime.datetime(2022, 8, 1, 0, 0, 0, 0),
    #         },
    #     },
    #     fields={"meta.applet.@id": 1},
    # )
    # applet_ids = []
    # for answer in answers:
    #     applet_ids.append(answer["meta"]["applet"]["@id"])

    # applets = Applet().find(
    #     query={
    #         "meta.applet.displayName": {"$exists": True},
    #         "meta.applet.deleted": {"$ne": True},
    #         "meta.applet.editing": {"$ne": True},
    #         "$or": [
    #             {
    #                 "created": {
    #                     "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
    #                 }
    #             },
    #             {
    #                 "updated": {
    #                     "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
    #                 }
    #             },
    #             {"_id": {"$in": applet_ids}},
    #         ],
    #     },
    #     fields={"_id": 1},
    # )
    migrating_applets = []
    # for applet in applets:
    #     migrating_applets.append(str(applet["_id"]))
    migrating_applets = []

    appletsCount = len(migrating_applets)
    print("total", appletsCount)
    # migrating_applets = migrating_applets[501:600]

    skipUntil = None
    skipped_applets = []
    for index, applet_id in enumerate(migrating_applets, start=1):
        # applet_id = str(applet_id["_id"])
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
                _applet.display_name = applet.display_name

            if applets != {}:
                applets[list(applets.keys())[-1]] = applet
            else:
                applets[applet.extra_fields["version"]] = applet

            await postgres.save_applets(applets, owner_id)
        except (FormatldException, EmptyAppletException) as e:
            print("Skipped because: ", e.message)
        # except Exception as e:
        #     skipped_applets.append(applet_id)
        #     print("error: ", applet_id)

    print("error in", len(skipped_applets), "applets:")
    print(skipped_applets)


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
