import asyncio
import datetime
import uuid
import csv
import argparse
import traceback

from bson.objectid import ObjectId

from apps.migrate.exception.exception import (
    FormatldException,
    EmptyAppletException,
)
from apps.migrate.services.mongo import Mongo, decrypt
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
    configure_report,
    migration_log,
    mongoid_to_uuid,
    intersection,
    get_arguments,
)
from infrastructure.database import session_manager


async def migrate_applets(
    migrating_applets: list[ObjectId], mongo: Mongo, postgres: Postgres
):
    migration_log.info("Applets migration start")
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
    migration_log.info("Applets to migrate total %s", appletsCount)

    skipUntil = None
    skipped_applets = []
    for index, applet_id in enumerate(migrating_applets, start=1):
        if skipUntil == applet_id:
            skipUntil = None
        if skipUntil is not None or applet_id in toSkip:
            continue
        migration_log.debug(
            "processing %s %s/%s", applet_id, index, appletsCount
        )
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
            skipped_applets.append([applet_id, e])
            migration_log.debug(
                "%s skipped because: %s", str(applet_id), e.message
            )
        except Exception as e:
            skipped_applets.append([applet_id, e])
            migration_log.debug("error: %s", applet_id)
    postgres.fix_empty_questions()
    migration_log.info("error in %s applets:", len(skipped_applets))
    for applet_id, e in skipped_applets:
        migration_log.info("%s: %s", str(applet_id), str(e))
    migration_log.info("Applets migration end")


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
        # hpa
        "5f0e35523477de8b4a528dd0",
        "5fd28283c47c585b7c73354b",
        "6116c49e66f506a576da4f03",
        "618bfecaa21eb6eb030e0393",
        "61e9b70562485608c74bfeb5",
        "61f3415f62485608c74c1f0b",
        "61f3419a62485608c74c1f25",
        "61f3423962485608c74c1f45",
        "61f34d4462485608c74c1fcd",
        "61f3517962485608c74c25d1",
        "62014137ace55b10691bf423",
        "62017372ace55b10691bf9a1",
        "6201cc26ace55b10691c0814",
        "6202734eace55b10691c0fc4",
        "6202738aace55b10691c101d",
        "6206e11ce0f9c9bd6be6c165",
        "6206e176e0f9c9bd6be6c488",
        "6206e1cfe0f9c9bd6be6c530",
        "6206e216e0f9c9bd6be6c587",
        "620bc550b0b0a55f680dbc1b",
        "620c1f28b0b0a55f680dc557",
        "620eb010b0b0a55f680dcec0",
        "620eb026b0b0a55f680dcee8",
        "620eb401b0b0a55f680dd5f5",
        "6210202db0b0a55f680de1a5",
        "623cb24d5197b9338bdaed65",
        "623cd7ee5197b9338bdaf218",
        "623ce1695197b9338bdaf388",
        "623ce52a5197b9338bdaf4b6",
        "623dfaf95197b9338bdaf8c5",
        "6276c0fd0a62aa105607838c",
        "62b1a90eb90b7f2ba9e1c3f1",
        "62d06045acd35a1054f106f6",
        "632bb2fab7ee9765ba542b29",
        "6376a89752ea0234e1f4ffdb",
        "639a1b83e0054c0ff596614c",
        "63ab106be0054c0ff596741b",
        "63ab1772e0054c0ff59683e5",
        "63ac4b27e0054c0ff59687d1",
        "63ac814ae0054c0ff5968cf3",
        "63ac82e7e0054c0ff5968f89",
        "63ad9075e0054c0ff5969586",
        "63ad97fae0054c0ff59698b5",
        "63b45736b71996101a0f50ed",
        "63b5ccf2b71996101a0f58b3",
        "63b83b4cb71996101a0f5fa3",
        "63b83d33b71996101a0f607f",
        "63b83dd6b71996101a0f60d1",
        "63d3d579b71996780cdf409a",
        "64078539601cdc5212d60c03",
        "6463d531a67ac10f93b46032",
        "648c7d0b8819c1120b4f7029",
        "648c7d0f8819c1120b4f709c",
        "648c802c8819c1120b4f719b",
        "648c80cd8819c1120b4f728d",
        "649362a18819c1120b4f8f9c",
        "64c975a422d8180cf9b3e426",
        "65240e723c36ce0d4d6ce324",
        "63a494b3e0054c0ff5966b7e",
        "63a607a6e0054c0ff5966f58",
        "63b5ce3eb71996101a0f59cd",
        "63a60a1be0054c0ff5967117",
        # Kramers Edits
        "629f7b34b90b7f104d02ed17",
        "629f7b4ab90b7f104d02eda5",
        "629f7b60b90b7f104d02ee99",
        "629f7b6bb90b7f104d02ef11",
        "629f7b84b90b7f104d02ef77",
        "629f7b8eb90b7f104d02f001",
        "634db4bd5cb700431121bb0d",
        "634db6e65cb700431121bb67",
        "634dbcc25cb700431121bbb1",
        "634ecde45cb700431121c9f4",
        "634ef3e15cb700431121cc77",
        "634ef5895cb700431121cccc",
        "634ef77f5cb700431121cd34",
        "634ef79a5cb700431121cd4c",
        "634efcb05cb700431121cd91",
        "634efcd65cb700431121cdc3",
        "634f00dc5cb700431121cf2d",
        "635a9f7d5cb700431121f771",
        "635fbdc85cb700431121f8fd",
        "635fbde65cb700431121f925",
        "635fbf645cb700431121f99b",
        "63657a675cb700431122013e",
        "636930ff52ea02101467611f",
        "6369409c52ea0210146764a8",
        "636940b852ea0210146764ce",
        "63696a7552ea021014676670",
        "6372937b52ea0234e1f4f660",
        "6377b1a252ea0234e1f501e6",
        "6377b1d152ea0234e1f5031a",
        "63864aed52ea0234e1f521da",
        "63864b1252ea0234e1f521fe",
        "6387b4ea52ea0234e1f5241d",
        "6387b69952ea0234e1f52462",
        "6388f7dc52ea0234e1f5253f",
        "6388ffb552ea0234e1f525dc",
        "638a330152ea0234e1f52720",
        "638a332752ea0234e1f52734",
        # Interns
        "62cdb038acd35a1054f0fcb2",
        "62cdb05cacd35a1054f0fce4",
        "62cdd687acd35a1054f0fdef",
        "62cdd693acd35a1054f0fe2d",
        "62d08352acd35a1054f107e2",
        "62d08394acd35a1054f1082c",
        "62d1861dacd35a1054f109e5",
        "62d18820acd35a1054f10a31",
        "62daac9bacd35a44dd03c9b5",
        "62dad2dcacd35a44dd03ca9a",
        "62e82dc7acd35a39e99b35e6",
        "62f16366acd35a39e99b57ec",
        "62f16376acd35a39e99b581e",
        "62f16387acd35a39e99b5842",
        "62f16393acd35a39e99b58ce",
        "62f16396acd35a39e99b58eb",
        "62f164edacd35a39e99b590c",
        "62f17b5bacd35a39e99b5a54",
        "634075a8b7ee9765ba5448b9",
        "63408143b7ee9765ba544921",
        "636425cf5cb700431121fe46",
        "636532fd5cb700431121ff93",
        "6365334c5cb7004311220087",
        "636533965cb70043112200a9",
        "6369362f52ea02101467626f",
        "6369364252ea021014676287",
        "6369368f52ea0210146763bb",
        "636936a652ea0210146763ef",
        "636936b352ea02101467640d",
        "636936ca52ea021014676437",
        "636936e652ea02101467645b",
        "636ae72a52ea021014676c79",
        "636af22f52ea021014676dc5",
        "636e942c52ea0234e1f4ec25",
        "637972fd52ea0234e1f50703",
        "637bddf852ea0234e1f5081b",
        "63e64894601cdc0fee1f1341",
        "6417580b83718f0fbf0b0afc",
        "6420f3d083718f0fbf0b3741",
        # RS2 Phenotypic Assessments - Individual Tests",
        "61faa6ad62485608c74c5d25",
        "61faa6d362485608c74c5d83",
        "61faa6e462485608c74c5da1",
        "61faa71f62485608c74c5e57",
        "61faa74762485608c74c5edc",
        "61faa75262485608c74c5ef7",
        "61faa77962485608c74c5f1f",
        "61faa79e62485608c74c5f56",
        "61faa7dd62485608c74c5fb2",
        "61faa80d62485608c74c6025",
        "61faa84362485608c74c607b",
        "61faa84f62485608c74c609c",
        "61faa8a162485608c74c615e",
        "61faa8b362485608c74c6180",
        "61faa8eb62485608c74c6273",
        "61faa8fa62485608c74c62e6",
        "61faa91b62485608c74c6338",
        "61faa92562485608c74c6352",
        "61faa93662485608c74c637c",
        "61faa94e62485608c74c63a7",
        "61faa98462485608c74c641f",
        "61faa9ba62485608c74c650f",
        "61faa9c162485608c74c6534",
        "61faaa4962485608c74c6a21",
        "61faaa5462485608c74c6a4b",
        "61faaa6b62485608c74c6aa2",
        "61faaa8e62485608c74c6b26",
        "61faaaa862485608c74c6b93",
        "61faaab062485608c74c6bb1",
        "61faaacb62485608c74c6bf6",
        "61faaaec62485608c74c6caa",
        "61faab2862485608c74c6e61",
        "61faab4a62485608c74c6ea3",
        "61faab7a62485608c74c7047",
        "61faaba362485608c74c70e2",
        "61faabe462485608c74c724e",
        "61faac0162485608c74c72c6",
        "61faac0c62485608c74c7319",
        "61faac1c62485608c74c7347",
        "61faac1c62485608c74c734b",
        "61faac2762485608c74c737f",
        "61faac4a62485608c74c73bd",
        "61faac8f62485608c74c756b",
        "61faaca762485608c74c75c4",
        "61faacc562485608c74c762a",
        "61faacd462485608c74c7653",
        "61faacf862485608c74c76a4",
        "61faad1062485608c74c76e2",
        "61faad1062485608c74c76e6",
        "61faad3462485608c74c771e",
        "61faad5162485608c74c7752",
        "61faad8162485608c74c7786",
        "61faad9d62485608c74c77bb",
        "61faadbd62485608c74c77e9",
        "61faaddc62485608c74c780e",
        "61faae0262485608c74c783c",
        "61faae1e62485608c74c7864",
        "61faae4d62485608c74c78b1",
        "61faae5b62485608c74c78d5",
        "61faae7962485608c74c78fa",
        "61faae9b62485608c74c791f",
        "61faaeca62485608c74c794f",
        "61faaed962485608c74c7979",
        "61faaefb62485608c74c79a7",
        "61faaf1b62485608c74c79db",
        "61faaf5262485608c74c7a09",
        "61faaf7562485608c74c7a3d",
        "61faaf9762485608c74c7a71",
        "61faafbb62485608c74c7aa5",
        "61fab00162485608c74c7ba1",
        "61fab01562485608c74c7bed",
        "61fab01662485608c74c7bfa",
        "61fab02762485608c74c7c26",
        "61fab04562485608c74c7c4e",
        "61fab07562485608c74c7cdf",
        "61fab08762485608c74c7d02",
        "61fab0bf62485608c74c7ddf",
        "61fab0d562485608c74c7e23",
        "61fab0d962485608c74c7e36",
        "61fab0fd62485608c74c7e7c",
        "61fab11c62485608c74c7ec3",
        "61fab13362485608c74c7ef3",
        "61fab16562485608c74c7fba",
        "61fab19162485608c74c8066",
        "61fab1ba62485608c74c80a0",
        "61fab2c562485608c74c80db",
        "61fab31462485608c74c811e",
        "61fab3c662485608c74c8161",
        "61fab40562485608c74c818d",
        "61fab43862485608c74c81b2",
        "62b5f714b90b7f2ba9e1d216",
        "62b60e08b90b7f2ba9e1d273",
        # other
        "62a8d7d7b90b7f2ba9e1aa43",
        "62a8d7e5b90b7f2ba9e1aab3",
        "62a8d7f9b90b7f2ba9e1ab92",
        "62a8d807b90b7f2ba9e1acbb",
        "63582fe95cb700431121f434",
        "635830a95cb700431121f491",
        "6369721852ea02101467689c",
        "636952b452ea021014676579",
        "63583c0c5cb700431121f4fd",
        "636a833152ea021014676b37",
        "636d2aad52ea021014677599",
        "636d2b5c52ea0210146775af",
        "636d2c9452ea0210146775c8",
        "636d2cc252ea0210146775d8",
        "636d2db352ea0210146775ff",
        "636d2de352ea02101467760f",
        "636d2ee652ea021014677631",
        "636d6e5352ea021014677837",
        "63b72a32b71996101a0f5bc9",
        "63d2e578b71996780cdf3d2f",
        "63d2e7c7b71996780cdf3d6a",
        "63d42f70b71996780cdf421f",
        "63efcedb601cdc5212d58634",
        "63efcf1f601cdc5212d586c8",
        "6358265b5cb700431121f033",
        "6358267b5cb700431121f143",
        "63696d4a52ea02101467671d",
        "63696e7c52ea021014676784",
        "6369750b52ea021014676a28",
        "63ab15d0e0054c0ff5967aac",
        # 32 final-final
        "63e16d80601cdc0fee1ea5f6",
        "63e17cc1601cdc0fee1ea753",
        "61dd9f93025fb7a0d647932c",
        "61dd9f9d025fb7a0d6479386",
        "61dda2b2025fb7a0d647959a",
        "61dda2c3025fb7a0d64795d9",
        "61dda422025fb7a0d647982f",
        "61dda42d025fb7a0d64798c4",
        "61e9c85462485608c74c000c",
        "61dd9f80025fb7a0d64792d3",
        "5fc51f0fc47c585b7c731bb1",
        "61dda1a9025fb7a0d6479502",
        "61dda34a025fb7a0d64796ea",
        "61dda359025fb7a0d647972c",
        "5fd94a47aadcee56e6ad6550",
        "6099aa8e42545caea069d426",
        "5fd26d9dc47c585b7c7334fa",
        "6099993f42545caea069d1f9",
        "5fc702ccc47c585b7c73223e",
        "5fce3d3ac47c585b7c733070",
        "60915b3842545caea069cc5e",
        "60b7d06b5fa6a85768b61fa3",
        "5fc91d18c47c585b7c732cdf",
        "5fadb305bdec546ce77b2f4e",
        "609f0d8a42545caea069dbb8",
        "5fc6a5a2c47c585b7c731fc6",
        "63e28a51601cdc0fee1eb2ab",
        "613f6eba6401599f0e495dc5",
        "62768ff20a62aa1056078093",
        "6307d801924264279508777d",
        "6324c0afb7ee9765ba54229f",
        "631aba1db7ee970ffa9009e3",
    ]
    for applet in applets:
        migrating_applets.append(str(applet["_id"]))

    excluded_applets = [
        "62a0c76fb90b7f2ba9e19651",
        "62dea832acd35a4bf1195b56",
        "62e3b406acd35a4c635b1ddb",
        "62eb8c23acd35a39e99b41b6",
        "62f63d07acd35a39e99b69aa",
        "63160c84b7ee970ffa90019c",
        "63171548b7ee970ffa9002f6",
        "6318827ab7ee970ffa900569",
        "6319a5feb7ee970ffa90082c",
        "63203221b7ee970ffa901067",
        "6347d89e5cb7004311219d5c",
        "6349475b5cb700431121a63f",
        "634eb7035cb700431121c783",
        "6352922c5cb700431121e6ea",
        "6368cf6352ea021014675e25",
        "636bd89b52ea021014676edd",
        "6376857c52ea0234e1f4fea1",
        "63c808bbb71996780cdf1158",
        "63e24542601cdc0fee1eafd4",
        "63e62535601cdc0fee1f11ca",
        "63f908fd601cdc5212d5b88d",
        "63ffcc37601cdc5212d5e4bd",
        "640978be601cdc5212d621c4",
        "640f146d83718f0fbf0adfc7",
        "6413a39f83718f0fbf0aff7b",
        "64149c8083718f0fbf0b0379",
        "6422892683718f0fbf0b4297",
        "642ec26783718f0fbf0b7996",
        "6447de3b25d51a0f8edb17ee",
        "64676a1ea67ac10f93b46c1a",
        "646f5cbaa67ac10f93b48108",
        "6474dc2fa67ac10f93b495e9",
        "6486ed5d8819c1120b4f5d81",
        "648713b08819c1120b4f5f26",
        "6493334d8819c1120b4f8611",
        "64f733f922d818224fd38d35",  # test applet
        "627be2e30a62aa47962268c7",  # broken items, no real responses
    ]
    migrating_applets = [
        applet_id
        for applet_id in migrating_applets
        if applet_id not in excluded_applets
    ]

    migrating_applets = list(set(migrating_applets))
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
    migration_log.info("Roles migration start")
    anon_id = postgres.get_anon_respondent()
    if not applet_ids:
        applet_ids = postgres.get_migrated_applets()
    roles = mongo.get_roles_mapping_from_applet_profile(applet_ids)
    roles += mongo.get_anons(anon_id)
    postgres.save_user_access_workspace(roles)
    migration_log.info("Roles migration end")


def migrate_user_pins(
    applets_ids: list | None, mongo: Mongo, postgres: Postgres
):
    migration_log.info("User pins migration start")
    pinned_dao = mongo.get_user_pin_mapping(applets_ids)
    migrated_ids = postgres.get_migrated_users_ids()
    to_migrate = []
    skipped = 0
    for profile in pinned_dao:
        if profile.user_id not in migrated_ids:
            migration_log.debug(
                f"user_id {profile.user_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        if profile.pinned_user_id not in migrated_ids:
            migration_log.debug(
                f"pinned_user_id {profile.user_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        if profile.owner_id not in migrated_ids:
            migration_log.debug(
                f"owner_id {profile.owner_id} not presented in PostgreSQL"
            )
            skipped += 1
            continue
        to_migrate.append(profile)
    rows_count = postgres.save_user_pins(to_migrate)
    migration_log.info(f"Inserted {rows_count} rows")
    migration_log.info("User pins migration end")


def migrate_folders(workspace_id: str | None, mongo, postgres):
    migration_log.info("Folders migration start")
    if workspace_id:
        ids = [mongoid_to_uuid(workspace_id)]
        workspaces = postgres.get_workspace_info(ids)
    else:
        workspaces = postgres.get_migrated_workspaces()
    migration_log.info("[FOLDERS] Fetch from Mongo")
    folders_dao, applet_dao = mongo.get_folder_mapping(workspaces)
    migrated, skipped = postgres.save_folders(folders_dao)
    migration_log.info(f"[FOLDERS] {migrated=}, {skipped=}")
    migration_log.info("[FOLDER_APPLETS] In progress")
    migrated, skipped = postgres.save_folders_applet(applet_dao)
    migration_log.info(f"[FOLDER_APPLETS] {migrated=}, {skipped=}")
    migration_log.info("Folders migration end")


def migrate_library(applet_ids: list[ObjectId] | None, mongo, postgres):
    migration_log.info("Library & themes migration start")
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

    applet_themes = mongo.get_applet_theme_mapping()
    applets_count = postgres.set_applets_themes(applet_themes)
    postgres.apply_default_theme()
    msg = postgres.themes_slice()
    migration_log.info(f"[LIBRARY] Migrated {lib_count}")
    migration_log.info(f"[THEME] Migrated {theme_count}")
    migration_log.info(f"[THEME] Applets with themes {applets_count}")
    migration_log.info(f"[THEME] {msg}")
    migration_log.info("Library & themes migration end")


async def migrate_events(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    migration_log.info("Events migration start")
    events_collection = mongo.db["events"]
    session = session_manager.get_session()

    events: list = []

    query = {}
    if applet_ids:
        query["applet_id"] = {"$in": applet_ids}

    for event in events_collection.find(query):
        events.append(MongoEvent.parse_obj(event))

    migration_log.info(f"Total number of events in mongo: {len(events)}")
    # assert len(events) == events_collection.estimated_document_count()

    await EventMigrationService(session, events).run_events_migration()
    migration_log.info("Events migration end")


async def add_default_events(
    applet_ids: list[ObjectId] | None, postgres: Postgres
):
    migration_log.info("Start adding default event to activities and flows")
    applets_ids = [str(mongoid_to_uuid(applet_id)) for applet_id in applet_ids]
    activities_without_events: list[
        tuple[str, str]
    ] = postgres.get_activities_without_activity_events(applets_ids)
    flows_without_events: list[
        tuple[str, str]
    ] = postgres.get_flows_without_activity_events(applets_ids)

    migration_log.info(
        f"Number of activities without default event: {len(activities_without_events)}"
    )
    migration_log.info(
        f"Number of flows without default event: {len(flows_without_events)}"
    )

    session = session_manager.get_session()
    await DefaultEventAddingService(
        session, activities_without_events, flows_without_events
    ).run_adding_default_event()

    migration_log.info("Finish adding default event to activities and flows")


async def migrate_alerts(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    migration_log.info("Alerts migration start")
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
                migration_log.debug(
                    f"[ALERTS] Skipped one of alerts because can't get applet version"
                )
                continue
            alerts.append(MongoAlert.parse_obj(alert))
        else:
            migration_log.debug(
                f"[ALERTS] Skipped one of alerts because can't get userId"
            )

    migration_log.info(
        f"[ALERTS] Total number of alerts in mongo for {len(applet_ids) if applet_ids else 'all'} applets: {len(alerts)}"
    )

    await AlertMigrationService(session, alerts).run_alerts_migration()
    migration_log.info("Alerts migration end")


async def migrate_pending_invitations(
    applet_ids: list[ObjectId] | None, mongo: Mongo, postgres: Postgres
):
    migration_log.info("Pending invitations migration start")
    invitations_collection = mongo.db["invitation"]
    session = session_manager.get_session()

    query = {}
    if applet_ids:
        query["appletId"] = {"$in": applet_ids}

    invitations: list = []
    for invitation in invitations_collection.find(query):
        try:
            invitations.append(MongoInvitation.parse_obj(invitation))
        except ValueError as e:
            migration_log.debug(
                f"[INVITATIONS] Skip invitation with id: {invitation['_id']} {e}"
            )

    migration_log.info(
        f"[INVITATIONS] Total number of pending invitations in mongo for {len(applet_ids) if applet_ids else 'all'} applets: {len(invitations)}"
    )

    await InvitationsMigrationService(
        session, invitations
    ).run_invitations_migration()
    migration_log.info("Pending invitations migration end")


async def migrate_public_links(postgres: Postgres, mongo: Mongo):
    migration_log.info("Public links migration start")
    applet_mongo_ids = postgres.get_migrated_applets()
    links = mongo.get_public_link_mappings(applet_mongo_ids)
    await postgres.save_public_link(links)
    migration_log.info("Public links migration start")


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

    # for applet_id in applets_ids:
    #     postgres.wipe_applet(str(applet_id))

    # Migrate applets, activities, items
    # await migrate_applets(applets_ids, mongo, postgres)

    # Extract failing applets info
    # info = extract_applet_info(mongo)
    # headers = list(info[0].keys())
    # with open("not_migrating.csv", "w") as file:
    #     writer = csv.DictWriter(file, fieldnames=headers)
    #     writer.writerows(info)

    # Migrate roles
    # migrate_roles(applets_ids, mongo, postgres)
    # # Migrate user pins
    # migrate_user_pins(applets_ids, mongo, postgres)
    # # Migrate folders
    # migrate_folders(workspace_id, mongo, postgres)
    # # Migrate library
    # migrate_library(applets_ids, mongo, postgres)
    # Migrate events
    # await migrate_events(applets_ids, mongo, postgres)

    # Add default (AlwayAvalible) events to activities and flows
    # await add_default_events(applets_ids, postgres)
    # Migrate alerts
    # await migrate_alerts(applets_ids, mongo, postgres)
    # Migrate pending invitation
    # await migrate_pending_invitations(applets_ids, mongo, postgres)

    # await migrate_public_links(postgres, mongo)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    args = get_arguments()
    configure_report(migration_log, args.report_file)
    asyncio.run(main(args.workspace, args.applet))
