import asyncio
import datetime
import csv

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
        "6202738aace55b10691c101d",  # broken conditional logic [object object]  in main applet
        "620eb401b0b0a55f680dd5f5",  # broken conditional logic [object object]  in main applet
        "6210202db0b0a55f680de1a5",  # broken conditional logic [object object]  in main applet
        "623ce52a5197b9338bdaf4b6",  # needs to be renamed in cache,version as well
        "62768ff20a62aa1056078093",  # broken flanker
        "627be2e30a62aa47962268c7",  # broken stability
        "62d06045acd35a1054f106f6",  # broken stability
        "635d04365cb700431121f8a1",  # chinese texts
        "63ebcec2601cdc0fee1f3d42",  # broken conditional logic in main applet
        "63ec1498601cdc0fee1f47d2",  # broken conditional logic in main applet
        "64934a618819c1120b4f8e34",  # duplicate name, needs to be renamed in cache
        "649465528819c1120b4f91cf",  # broken js expression in subscales in main applet
        "64946e208819c1120b4f9271",  # broken stimulus
    ]

    # applets = Applet().find(
    #     query={"_id": ObjectId("5fa5a276bdec546ce77b298b")}, fields={"_id": 1}
    # )

    answers = Item().find(
        query={
            "meta.dataSource": {"$exists": True},
            "created": {
                "$gte": datetime.datetime(2022, 8, 1, 0, 0, 0, 0),
            },
        },
        fields={"meta.applet.@id": 1},
    )
    applet_ids = []
    for answer in answers:
        applet_ids.append(answer["meta"]["applet"]["@id"])

    applets = Applet().find(
        query={
            "meta.applet.displayName": {"$exists": True},
            "meta.applet.deleted": {"$ne": True},
            "meta.applet.editing": {"$ne": True},
            "$or": [
                {
                    "created": {
                        "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
                    }
                },
                {
                    "updated": {
                        "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
                    }
                },
                {"_id": {"$in": applet_ids}},
            ],
        },
        fields={"_id": 1},
    )
    migrating_applets = []
    for applet in applets:
        migrating_applets.append(str(applet["_id"]))

    appletsCount = len(migrating_applets)
    print("total", appletsCount)

    skipUntil = None
    skipped_applets = []
    for index, applet_id in enumerate(migrating_applets, start=1):
        if skipUntil == applet_id:
            skipUntil = None
        if skipUntil is not None or applet_id in toSkip:
            continue
        print("processing", applet_id, index, "/", appletsCount)
        try:
            applet: dict | None = await mongo.get_applet(applet_id)

            applets, owner_id = await mongo.get_applet_versions(applet_id)
            for version, _applet in applets.items():
                _applet.extra_fields["created"] = applet.extra_fields[
                    "created"
                ]
                _applet.display_name = applet.display_name
                _applet.encryption = applet.encryption

            if applets != {}:
                applets[list(applets.keys())[-1]] = applet
            else:
                applets[applet.extra_fields["version"]] = applet

            await postgres.save_applets(applets, owner_id)
        except (FormatldException, EmptyAppletException) as e:
            print("Skipped because: ", e.message)
        except Exception as e:
            skipped_applets.append(applet_id)
            print("error: ", applet_id)

    print("error in", len(skipped_applets), "applets:")
    print(skipped_applets)


# def extract_applet_info(mongo: Mongo):
#     answers = Item().find(
#         query={
#             "meta.dataSource": {"$exists": True},
#             "created": {
#                 "$gte": datetime.datetime(2022, 8, 1, 0, 0, 0, 0),
#             },
#         },
#         fields={"meta.applet.@id": 1},
#     )
#     applet_ids = []
#     for answer in answers:
#         applet_ids.append(answer["meta"]["applet"]["@id"])

#     applets = Applet().find(
#         query={
#             "meta.applet.displayName": {"$exists": True},
#             "meta.applet.deleted": {"$ne": True},
#             "meta.applet.editing": {"$ne": True},
#             "$or": [
#                 {
#                     "created": {
#                         "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
#                     }
#                 },
#                 {
#                     "updated": {
#                         "$gte": datetime.datetime(2023, 2, 1, 0, 0, 0, 0),
#                     }
#                 },
#                 {"_id": {"$in": applet_ids}},
#             ],
#         },
#         fields={"_id": 1},
#     )
#     migrating_applets = []
#     for applet in applets:
#         migrating_applets.append(applet["_id"])

#     not_migrating = Applet().find(
#         query={
#             "meta.applet.displayName": {"$exists": True},
#             "meta.applet.deleted": {"$ne": True},
#             "meta.applet.editing": {"$ne": True},
#             "_id": {"$nin": migrating_applets},
#         },
#         fields={"_id": 1},
#     )
#     not_migrating_applets = []
#     print(not_migrating.count())
#     for applet in not_migrating:
#         not_migrating_applets.append(applet["_id"])

#     info = []
#     for applet in not_migrating_applets:
#         info.append(mongo.get_applet_info(applet))

#     return info


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

    # Extract failing applets info
    # info = extract_applet_info(mongo)
    # headers = list(info[0].keys())
    # with open("not_migrating.csv", "w") as file:
    #     writer = csv.DictWriter(file, fieldnames=headers)
    #     writer.writerows(info)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
