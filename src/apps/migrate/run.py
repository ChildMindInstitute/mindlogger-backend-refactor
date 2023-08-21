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
        # "63bd5736aba6fd499bda0fee",  # subscales refer to name (question: Put your name)
        # # "63be5c97aba6fd499bda1960",  # Totalscoretable incorrect raw score '~10~0' - fixed
        # "63be9739aba6fd499bda1eea",  # subscale refer to text item, instead of single,multi, slider
        # "63c00872aba6fd499bda2990",  # subscale refer to text item, instead of single,multi, slider
        # # "63be9916aba6fd499bda1fd5",  # incorrect github url
        # # "63be6ce5aba6fd499bda1b43",  # js expression error TODO check jsexpression and whole doc
        # # "63bd5734aba6fd499bda0fe3",  # flow has activity that is being duplicated from another applet.
        # # "63c52d2aaba6fd499bda35e1",  # converter not parsing score conditions
        # # "63e4efd41d3f3e0f89b488bd",  # wrong context file in activity for 2-version
        # # "63f722ed1d3f3e0f89b488d8",  # applet name duplicates
        # # "6411c4dbeddaf60f21c3a04c",  # score conditional names are same
        # # "64243279eddaf60f21c3a5e7",  # duplicate name as 64243253eddaf60f21c3a5c5 proposal: set first versions name as last ones
        # # "62ece4c8154fa81f3efe729b",  # wrong context file in activity for 2-version
        # "6111da9bfef711e5392f2efc",  # broken test applet
        # "640978be601cdc5212d621c4",  # broken CL logic for items , Alena
        # # prod
        # "5fa5a276bdec546ce77b298b",  # broken subscale in history
        # "5fadb305bdec546ce77b2f4e",  # NP
        # "5fc51f0fc47c585b7c731bb1",  # broken document
        # "5fc6a5a2c47c585b7c731fc6",  # broken document
        # "5fc702ccc47c585b7c73223e",  # broken document
        # "5fce3d3ac47c585b7c733070",  # broken document
        # "5fd26d9dc47c585b7c7334fa",  # broken document
        # "5fd94ee9aadcee56e6ad6599",  # broken document
        # "6099792a42545caea069cf8f",  # broken document
        # "609f0d8a42545caea069dbb8",  # broken document
        # "60b7d06b5fa6a85768b61fa3",  # broken document
        # "60ddb7645fa6a85768b6621d",  # broken document
    ]
    # applets = Applet().find(
    #     query={"_id": ObjectId("63be5c97aba6fd499bda1960")}, fields={"_id": 1}
    # )
    # applets = Applet().find(query={'_id': ObjectId('64d0de7e5e3d9e04c28a1720')}, fields={"_id": 1}) # TODO: 6.2.6 6.2.7 ???
    # applets = Applet().find(
    #     query={"_id": ObjectId("64243279eddaf60f21c3a5e7")}, fields={"_id": 1}
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

    appletsCount = applets.count()
    print("total", appletsCount)

    skipUntil = None
    skipped_applets = []
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
                _applet.display_name = applet.display_name

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

        print("error in", len(skipped_applets), "applets")


async def migrate_roles(mongo: Mongo, postgres: Postgres):
    applet_ids = postgres.get_migrated_applets()
    roles = mongo.get_user_applet_role_mapping(applet_ids)
    await postgres.save_user_access_workspace(roles)


async def migrate_user_pins(mongo: Mongo, postgres: Postgres):
    pinned_dao = mongo.get_user_pin_mapping()
    migrated_ids = postgres.get_migrated_users_ids()
    count = 0
    for profile in pinned_dao:
        if profile.user_id in migrated_ids:
            count += 1
    print(count)


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
    # await migrate_applets(mongo, postgres)
    # await migrate_roles(mongo, postgres)
    await migrate_user_pins(mongo, postgres)
    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
