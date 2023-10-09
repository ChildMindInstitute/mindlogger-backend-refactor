import asyncio
import datetime
import uuid
import csv
import argparse

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
from apps.migrate.services.default_event_service import (
    DefaultEventAddingService,
)
from apps.migrate.services.alert_service import (
    MongoAlert,
    AlertMigrationService,
)
from apps.migrate.services.invitation_service import (
    MongoInvitation,
    InvitationsMigrationService,
)
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.models.item import Item


from apps.migrate.utilities import (
    migration_log,
    mongoid_to_uuid,
    intersection,
    get_arguments,
)
from infrastructure.database import session_manager


async def migrate_applets(
    migrating_applets: list[ObjectId], mongo: Mongo, postgres: Postgres
):
    toSkip = [
        "635d04365cb700431121f8a1",  # chinese texts
    ]

    # applets = list(
    #     Applet().find(
    #         query={
    #             "_id": ObjectId("64cd2c6a22d8180cf9b3f1ba")
    #         },  # 64cd2c7922d8180cf9b3f1fa
    #         fields={"_id": 1}
    #         # query={"accountId": {'$in': [ObjectId("64c2395b8819c178d236685b"), ObjectId("64e7a92522d81858d681d2c3")]}}, fields={"_id": 1}
    #         # query={"_id": {'$in': [
    #         #     ObjectId('62f6261dacd35a39e99b6870'), ObjectId('633ecc1ab7ee9765ba54452d'), ObjectId('633fc997b7ee9765ba5447f3'), ObjectId('633fc9b7b7ee9765ba544820'), ObjectId('63762e1a52ea0234e1f4fdfe'), ObjectId('63c946dfb71996780cdf17dc'), ObjectId('63e36745601cdc0fee1ec750'), ObjectId('63f5cdb8601cdc5212d5a3d5'), ObjectId('640b239b601cdc5212d63e75'), ObjectId('647486d4a67ac10f93b48fef'), ObjectId('64cd2c7922d8180cf9b3f1fa'), ObjectId('64d4cd2522d8180cf9b40b3d'), ObjectId('64dce2d622d81858d6819f13'), ObjectId('64e7abb122d81858d681d957'), ObjectId('64e7af5e22d81858d681de92')
    #         # ]}}, fields={"_id": 1}
    #     )
    # )

    # migrating_applets = [
    #     "61dda090025fb7a0d64793d8",
    #     "62b339f7b90b7f2ba9e1c818",
    #     "5f0e35523477de8b4a528dd0",
    #     "61dda0b5025fb7a0d64793f9",
    #     "6437d20425d51a0f8edae5f4",
    #     "61dd9f5d025fb7a0d6479259",
    # ]

    migrating_applets = [str(applet_id) for applet_id in migrating_applets]

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
            if applets != {}:
                if applet.extra_fields["version"] != list(applets.keys())[-1]:
                    applet.extra_fields["version"] = list(applets.keys())[-1]

                applets[list(applets.keys())[-1]] = applet
            else:
                applets[applet.extra_fields["version"]] = applet

            for version, _applet in applets.items():
                _applet.extra_fields["created"] = applet.extra_fields[
                    "created"
                ]
                _applet.display_name = applet.display_name
                _applet.encryption = applet.encryption

            await postgres.save_applets(applets, owner_id)
        except (FormatldException, EmptyAppletException) as e:
            print("Skipped because: ", e.message)
        except Exception as e:
            skipped_applets.append(applet_id)
            print("error: ", applet_id)
    postgres.fix_empty_questions()
    print("error in", len(skipped_applets), "applets:")
    print(skipped_applets)


async def get_applets_ids() -> list[str]:
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
    migrating_applets = [
        # lpi arbitrary
        "6116c49e66f506a576da4f03",
        "61e82fd5d2d27f6294c2c58d",
        "61d7538d025fb7a0d6478ed8",
        "61e1446fbf09cb40db5a2f09",
        "613f7a206401599f0e495e0a",
        "61de845486e8fa4e453200bd",
        "61def12cbf09cb40db5a2a9f",
        "61d6b7e328a1737acc8e3322",
        "61498e7befa8adf9de386deb",
        "61d5df0c28a1737acc8e32df",
        "623e26175197b9338bdafbf0",
        "61ddc1d186e8fa4e45320087",
        "61dc9ee85f3caf2dffb40342",
        "61e03e4abf09cb40db5a2cb4",
        "61c485603ea2036de3aa53e0",
        "5fd28283c47c585b7c73354b",
        "61e8234fd2d27f6294c2c519",
        "5f0e35523477de8b4a528dd0",
        "6238d2935197b94689825c71",
        "625569663b4f351025643ff5",
        "61e82aabd2d27f6294c2c547",
        "61b2103b9c4ebd9574b0511e",
        "61e82a8ed2d27f6294c2c535",
        "61e8359fd2d27f6294c2c5e8",
        "61bd0bc67a53e1f8c9862b21",
        "61e52ccb86e8fa4e453205de",
        "61de837586e8fa4e453200a5",
        "61e831f7d2d27f6294c2c5b2",
        "61690789bf3a525a9668e6d6",
        "61e03cbebf09cb40db5a2c80",
        # miresource arbitrary
        "62d06045acd35a1054f106f6",
        "638df6eb52ea0234e1f52ab7",
        "62dd5af4154fa81092ab2570",
        "632b451a31f2c270dff11c11",
        "638df5b452ea0234e1f52a8a",
    ]
    for applet in applets:
        migrating_applets.append(str(applet["_id"]))

    return migrating_applets


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


def migrate_roles(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    migration_log.warning("Start Role migration")
    anon_id = postgres.get_anon_respondent()
    if not applet_ids:
        applet_ids = postgres.get_migrated_applets()
    roles = mongo.get_user_applet_role_mapping(applet_ids)
    roles += mongo.get_anons(anon_id)
    postgres.save_user_access_workspace(roles)
    migration_log.warning("Role has been migrated")


def migrate_user_pins(
    applets_ids: list | None, mongo: Mongo, postgres: Postgres
):
    migration_log.warning("Start UserPins migration")
    pinned_dao = mongo.get_user_pin_mapping(applets_ids)
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


def migrate_folders(workspace_id: str | None, mongo, postgres):
    migration_log.warning("[FOLDERS] In progress")
    if workspace_id:
        workspaces_ids = [mongoid_to_uuid(workspace_id)]
    else:
        workspaces_ids = postgres.get_migrated_workspaces()
    folders_dao, applet_dao = mongo.get_folder_mapping(workspaces_ids)
    migrated, skipped = postgres.save_folders(folders_dao)
    migration_log.warning(f"[FOLDERS] {migrated=}, {skipped=}")
    migration_log.warning("[FOLDER_APPLETS] In progress")
    migrated, skipped = postgres.save_folders_applet(applet_dao)
    migration_log.warning(f"[FOLDER_APPLETS] {migrated=}, {skipped=}")


def migrate_library(applet_ids: list[ObjectId] | None, mongo, postgres):
    lib_count = 0
    theme_count = 0
    lib_set, theme_set = mongo.get_library(applet_ids)
    for lib in lib_set:
        if lib.applet_id_version is None:
            version = postgres.get_latest_applet_id_version(lib.applet_id)
            lib.applet_id_version = version
            if version is None:
                continue
        keywords = postgres.get_applet_library_keywords(
            applet_id=lib.applet_id, applet_version=lib.applet_id_version
        )
        lib.search_keywords = keywords + lib.keywords
        success = postgres.save_library_item(lib)
        if success:
            lib_count += 1

    for theme in theme_set:
        success = postgres.save_theme_item(theme)
        if success:
            theme_count += 1
            postgres.add_theme_to_applet(theme.applet_id, theme.id)
    postgres.apply_default_theme()
    migration_log.warning(f"[LIBRARY] Migrated {lib_count}")
    migration_log.warning(f"[THEME] Migrated {theme_count}")


async def migrate_events(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    events_collection = mongo.db["events"]
    session = session_manager.get_session()

    events: list = []

    query = {}
    if applet_ids:
        query["applet_id"] = {"$in": applet_ids}

    for event in events_collection.find(query):
        events.append(MongoEvent.parse_obj(event))

    print(f"Total number of events in mongo: {len(events)}")
    # assert len(events) == events_collection.estimated_document_count()

    await EventMigrationService(session, events).run_events_migration()


async def add_default_evets(applet_ids: list[ObjectId] | None, postgres: Postgres):
    migration_log.warning(
        "Started adding default event to activities and flows"
    )
    applets_ids = [str(mongoid_to_uuid(applet_id)) for applet_id in applet_ids]
    activities_without_events: list[
        tuple[str, str]
    ] = postgres.get_activities_without_activity_events(applets_ids)
    flows_without_events: list[
        tuple[str, str]
    ] = postgres.get_flows_without_activity_events(applets_ids)

    migration_log.warning(
        f"Number of activities without default event: {len(activities_without_events)}"
    )
    migration_log.warning(
        f"Number of flows without default event: {len(flows_without_events)}"
    )

    session = session_manager.get_session()
    await DefaultEventAddingService(
        session, activities_without_events, flows_without_events
    ).run_adding_default_event()

    migration_log.warning(
        "Finished adding default event to activities and flows"
    )


async def migrate_alerts(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    alerts_collection = mongo.db["responseAlerts"]
    applet_profile_collection = mongo.db["appletProfile"]
    session = session_manager.get_session()

    query = {}
    if applet_ids:
        query["appletId"] = {"$in": applet_ids}

    alerts: list = []
    for alert in alerts_collection.find(query):
        applet_profile = applet_profile_collection.find_one(
            {"_id": alert["profileId"]}
        )
        if applet_profile and applet_profile.get("userId"):
            alert["user_id"] = applet_profile["userId"]
            version = postgres.get_applet_verions(
                mongoid_to_uuid(alert["appletId"])
            )
            if version:
                alert["version"] = version
            else:
                migration_log.warning(
                    f"[ALERTS] Skipped one of alerts because can't get applet version"
                )
                continue
            alerts.append(MongoAlert.parse_obj(alert))
        else:
            migration_log.warning(
                f"[ALERTS] Skipped one of alerts because can't get userId"
            )

    migration_log.warning(
        f"[ALERTS] Total number of alerts in mongo for {len(applet_ids) if applet_ids else 'all'} applets: {len(alerts)}"
    )

    await AlertMigrationService(session, alerts).run_alerts_migration()


async def migrate_pending_invitations(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    invitations_collection = mongo.db["invitation"]
    session = session_manager.get_session()

    query = {}
    if applet_ids:
        query["appletId"] = {"$in": applet_ids}

    invitations: list = []
    for invitation in invitations_collection.find(query):
        invitations.append(MongoInvitation.parse_obj(invitation))

    migration_log.warning(
        f"[INVITATIONS] Total number of pending invitations in mongo for {len(applet_ids) if applet_ids else 'all'} applets: {len(invitations)}"
    )

    await InvitationsMigrationService(
        session, invitations
    ).run_invitations_migration()


async def migrate_public_links(postgres: Postgres, mongo: Mongo):
    migration_log.warning("[PUBLIC LINKS] Started")
    applet_mongo_ids = postgres.get_migrated_applets()
    links = mongo.get_public_link_mappings(applet_mongo_ids)
    await postgres.save_public_link(links)
    migration_log.warning("[PUBLIC LINKS] Finished")


async def main(workspace_id: str | None, applets_ids: list[str] | None):
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    # users: list[dict] = mongo.get_users()
    # users_mapping = postgres.save_users(users)
    # await postgres.create_anonymous_respondent()
    # Migrate with users_workspace
    # workspaces = mongo.get_users_workspaces(list(users_mapping.keys()))
    # postgres.save_users_workspace(workspaces, users_mapping)

    allowed_applets_ids = await get_applets_ids()

    if workspace_id:
        applets_ids = intersection(
            mongo.get_applets_by_workspace(workspace_id), allowed_applets_ids
        )
    elif not applets_ids:
        applets_ids = allowed_applets_ids

    applets_ids = [ObjectId(applet_id) for applet_id in applets_ids]

    for applet_id in applets_ids:
        postgres.wipe_applet(str(applet_id))

    # Migrate applets, activities, items
    await migrate_applets(applets_ids, mongo, postgres)

    # Extract failing applets info
    # info = extract_applet_info(mongo)
    # headers = list(info[0].keys())
    # with open("not_migrating.csv", "w") as file:
    #     writer = csv.DictWriter(file, fieldnames=headers)
    #     writer.writerows(info)

    # # Migrate roles
    # migrate_roles(applets_ids, mongo, postgres)
    # # Migrate user pins
    # migrate_user_pins(applets_ids, mongo, postgres)
    # # Migrate folders
    # migrate_folders(workspace_id, mongo, postgres)
    # # Migrate library
    # migrate_library(applets_ids, mongo, postgres)
    # # Migrate events
    # await migrate_events(applets_ids, mongo, postgres)

    # Add default (AlwayAvalible) events to activities and flows
    # await add_default_evets(applets_ids, postgres)
    # Migrate alerts
    # await migrate_alerts(applets_ids, mongo, postgres)
    # Migrate pending invitation
    # await migrate_pending_invitations(applets_ids, mongo, postgres)

    # await migrate_public_links(postgres, mongo)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    workspace, applets = get_arguments()
    asyncio.run(main(workspace, applets))
