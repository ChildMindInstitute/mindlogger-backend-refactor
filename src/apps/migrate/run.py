import asyncio
import datetime
import uuid
import csv

from bson.objectid import ObjectId

from apps.migrate.exception.exception import (
    FormatldException,
    EmptyAppletException,
)
from apps.migrate.services.mongo import Mongo
from apps.migrate.services.postgres import Postgres
from apps.migrate.services.event_service import (
    MongoEvent,
    EventMigrationService,
)
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.models.item import Item


from apps.migrate.utilities import migration_log
from infrastructure.database import session_manager


async def migrate_applets(mongo: Mongo, postgres: Postgres):
    toSkip = [
        "635d04365cb700431121f8a1",  # chinese texts
    ]

    # applets = list(Applet().find(
    #     query={"_id": ObjectId("62768ff20a62aa1056078093")}, fields={"_id": 1}
    #     # query={"accountId": {'$in': [ObjectId("64c2395b8819c178d236685b"), ObjectId("64e7a92522d81858d681d2c3")]}}, fields={"_id": 1}
    #     # query={"_id": {'$in': [
    #     #     ObjectId('62f6261dacd35a39e99b6870'), ObjectId('633ecc1ab7ee9765ba54452d'), ObjectId('633fc997b7ee9765ba5447f3'), ObjectId('633fc9b7b7ee9765ba544820'), ObjectId('63762e1a52ea0234e1f4fdfe'), ObjectId('63c946dfb71996780cdf17dc'), ObjectId('63e36745601cdc0fee1ec750'), ObjectId('63f5cdb8601cdc5212d5a3d5'), ObjectId('640b239b601cdc5212d63e75'), ObjectId('647486d4a67ac10f93b48fef'), ObjectId('64cd2c7922d8180cf9b3f1fa'), ObjectId('64d4cd2522d8180cf9b40b3d'), ObjectId('64dce2d622d81858d6819f13'), ObjectId('64e7abb122d81858d681d957'), ObjectId('64e7af5e22d81858d681de92')
    #     # ]}}, fields={"_id": 1}
    # ))

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
        # postgres.wipe_applet(str(applet["_id"]))
        migrating_applets.append(str(applet["_id"]))
    # migrating_applets = [
    #     "6202738aace55b10691c101d",  # broken conditional logic [object object]  in main applet
    #     "620eb401b0b0a55f680dd5f5",  # broken conditional logic [object object]  in main applet
    #     "6210202db0b0a55f680de1a5",  # broken conditional logic [object object]  in main applet
    # ]

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


def migrate_roles(mongo: Mongo, postgres: Postgres):
    migration_log.warning("Start Role migration")
    applet_ids = postgres.get_migrated_applets()
    roles = mongo.get_user_applet_role_mapping(applet_ids)
    postgres.save_user_access_workspace(roles)
    migration_log.warning("Role has been migrated")


def migrate_user_pins(mongo: Mongo, postgres: Postgres):
    migration_log.warning("Start UserPins migration")
    pinned_dao = mongo.get_user_pin_mapping()
    migrated_ids = postgres.get_migrated_users_ids()
    to_migrate = []
    skipped = 0
    for profile in pinned_dao:
        if profile.user_id not in migrated_ids:
            migration_log.warning(
                f"user_id {profile.user_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        if profile.pinned_user_id not in migrated_ids:
            migration_log.warning(
                f"pinned_user_id {profile.user_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        if profile.owner_id not in migrated_ids:
            migration_log.warning(
                f"owner_id {profile.owner_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        to_migrate.append(profile)
    postgres.save_user_pins(to_migrate)
    migration_log.warning("UserPins has been migrated")


def migrate_folders(mongo, postgres):
    migration_log.warning("[FOLDERS] In progress")
    workspaces_ids = postgres.get_migrated_workspaces()
    folders_dao, applet_dao = mongo.get_folder_mapping(workspaces_ids)
    migrated, skipped = postgres.save_folders(folders_dao)
    migration_log.warning(f"[FOLDERS] {migrated=}, {skipped=}")
    migration_log.warning("[FOLDER_APPLETS] In progress")
    migrated, skipped = postgres.save_folders_applet(applet_dao)
    migration_log.warning(f"[FOLDER_APPLETS] {migrated=}, {skipped=}")


async def migrate_events(mongo: Mongo, postgres: Postgres):
    events_collection = mongo.db["events"]
    session = session_manager.get_session()

    events: list = []
    for event in events_collection.find():
        events.append(MongoEvent.parse_obj(event))

    print(f"Total number of events in mongo: {len(events)}")
    # assert len(events) == events_collection.estimated_document_count()

    await EventMigrationService(session, events).run_events_migration()


async def main():
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    users: list[dict] = mongo.get_users()
    users_mapping = postgres.save_users(users)

    # Migrate with users_workspace
    workspaces = mongo.get_users_workspaces(list(users_mapping.keys()))
    postgres.save_users_workspace(workspaces, users_mapping)

    # Migrate applets, activities, items
    await migrate_applets(mongo, postgres)

    # Extract failing applets info
    # info = extract_applet_info(mongo)
    # headers = list(info[0].keys())
    # with open("not_migrating.csv", "w") as file:
    #     writer = csv.DictWriter(file, fieldnames=headers)
    #     writer.writerows(info)

    # Migrate roles
    migrate_roles(mongo, postgres)
    # Migrate user pins
    migrate_user_pins(mongo, postgres)
    # Migrate folders
    migrate_folders(mongo, postgres)

    # Migrate events
    await migrate_events(mongo, postgres)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
