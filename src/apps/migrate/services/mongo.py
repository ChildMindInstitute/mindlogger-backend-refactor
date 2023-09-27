import datetime
import hashlib
import json
import os
import uuid
from functools import partial
from typing import List, Set, Tuple

from bson.objectid import ObjectId

from Cryptodome.Cipher import AES
from pymongo import ASCENDING, MongoClient
from sqlalchemy.types import String
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType

from apps.applets.domain.base import Encryption
from apps.girderformindlogger.models.account_profile import AccountProfile
from apps.girderformindlogger.models.activity import Activity
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.models.folder import Folder as FolderModel
from apps.girderformindlogger.models.profile import Profile
from apps.girderformindlogger.models.user import User
from apps.girderformindlogger.models.item import Item
from apps.girderformindlogger.utility import jsonld_expander
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)
from apps.migrate.data_description.applet_user_access import AppletUserDAO
from apps.migrate.data_description.folder_dao import FolderAppletDAO, FolderDAO
from apps.migrate.data_description.library_dao import LibraryDao, ThemeDao
from apps.migrate.data_description.user_pins import UserPinsDAO
from apps.migrate.exception.exception import (
    EmptyAppletException,
    FormatldException,
)
from apps.migrate.services.applet_versions import (
    CONTEXT,
    content_to_jsonld,
    get_versions_from_content,
)
from apps.migrate.utilities import (
    convert_role,
    migration_log,
    mongoid_to_uuid,
    uuid_to_mongoid,
)
from apps.shared.domain.base import InternalModel, PublicModel
from apps.shared.encryption import encrypt, get_key
from apps.workspaces.domain.constants import Role


enc = StringEncryptedType(key=get_key())


def decrypt(data):
    aes_key = bytes(str(os.getenv("MONGO__AES_KEY")).encode("utf-8"))
    max_count = 4

    try:
        cipher = AES.new(aes_key, AES.MODE_EAX, nonce=data[-32:-16])
        plaintext = cipher.decrypt(data[:-32])
        cipher.verify(data[-16:])
    except Exception:
        return None

    txt = plaintext.decode("utf-8")
    length = int(txt[-max_count:])

    return txt[:length]


def patch_broken_applet_versions(applet_id: str, applet_ld: dict) -> dict:
    broken_applet_versions = [
        "6201cc26ace55b10691c0814",
        "6202734eace55b10691c0fc4",
        "623b757b5197b9338bdae930",
        "623cd7ee5197b9338bdaf218",
        "623e26175197b9338bdafbf0",
        "627be9f60a62aa47962269b7",
        "62f2ce4facd35a39e99b5e92",
        "634715115cb70043112196ba",
        "63ca78b7b71996780cdf1f16",
        "63dd2d4eb7199623ac5002e4",
        "6202738aace55b10691c101d",
        "620eb401b0b0a55f680dd5f5",
        "6210202db0b0a55f680de1a5",
        "63ebcec2601cdc0fee1f3d42",
        "63ec1498601cdc0fee1f47d2",
    ]
    if applet_id in broken_applet_versions:
        for activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            for property in activity["reprolib:terms/addProperties"]:
                property["reprolib:terms/isVis"] = [{"@value": True}]

    broken_applet_abtrails = [
        "62768ff20a62aa1056078093",
        "62d06045acd35a1054f106f6",
        "64946e208819c1120b4f9271",
    ]
    if (
        applet_id == "62768ff20a62aa1056078093"
        and applet_ld["schema:version"][0]["@value"] == "1.0.4"
    ):
        applet_ld["reprolib:terms/order"][0]["@list"].pop(4)

    no_ids_flanker_map = {
        "<<<<<": "left-con",
        "<<><<": "right-inc",
        ">><>>": "left-inc",
        ">>>>>": "right-con",
        "--<--": "left-neut",
        "-->--": "right-neut",
    }
    if applet_id in broken_applet_abtrails:
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            if _activity["@id"] == "Flanker_360":
                for _item in _activity["reprolib:terms/order"][0]["@list"]:
                    if "reprolib:terms/inputs" in _item:
                        for _intput in _item["reprolib:terms/inputs"]:
                            if "schema:itemListElement" in _intput:
                                for _el in _intput["schema:itemListElement"]:
                                    if (
                                        "@id" not in _el
                                        and "schema:image" in _el
                                    ):
                                        _el["@id"] = no_ids_flanker_map[
                                            _el["schema:image"]
                                        ]
                        _item["reprolib:terms/inputs"].append(
                            {
                                "@type": ["http://schema.org/Text"],
                                "http://schema.org/name": [
                                    {"@language": "en", "@value": "blockType"}
                                ],
                                "http://schema.org/value": [
                                    {"@language": "en", "@value": "practice"}
                                ],
                            }
                        )
                        _item["reprolib:terms/inputs"].append(
                            {
                                "@type": ["http://schema.org/ItemList"],
                                "schema:itemListElement": [
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 1",
                                            }
                                        ],
                                        "schema:value": [{"@value": 0}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 2",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 3",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 4",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 5",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                ],
                                "schema:name": [
                                    {"@language": "en", "@value": "blocks"}
                                ],
                                "schema:numberOfItems": [{"@value": 5}],
                            }
                        )
                        _item["reprolib:terms/inputs"].append(
                            {
                                "schema:itemListElement": [
                                    {
                                        "schema:image": "",
                                        "schema:name": [
                                            {"@language": "en", "@value": "<"}
                                        ],
                                        "schema:value": [{"@value": 0}],
                                    },
                                    {
                                        "schema:image": "",
                                        "schema:name": [
                                            {"@language": "en", "@value": ">"}
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                ],
                                "schema:name": [
                                    {"@language": "en", "@value": "buttons"}
                                ],
                            }
                        )

    applet_ld = patch_prize_activity(applet_id, applet_ld)

    return applet_ld


def patch_broken_applets(
    applet_id: str, applet_ld: dict, applet_mongo: dict
) -> tuple[dict, dict]:
    broken_applets = [
        # broken conditional logic [object object]  in main applet
        "6202738aace55b10691c101d",
        "620eb401b0b0a55f680dd5f5",
        "6210202db0b0a55f680de1a5",
    ]
    if applet_id in broken_applets:
        for activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            for property in activity["reprolib:terms/addProperties"]:
                if type(
                    property["reprolib:terms/isVis"][0]["@value"]
                ) == str and (
                    "[object object]"
                    in property["reprolib:terms/isVis"][0]["@value"]
                ):
                    property["reprolib:terms/isVis"] = [{"@value": True}]

    # "623ce52a5197b9338bdaf4b6",  # needs to be renamed in cache,version as well
    broken_applet_name = [
        "623ce52a5197b9338bdaf4b6",
        "64934a618819c1120b4f8e34",
    ]
    if applet_id in broken_applet_name:
        applet_ld["displayName"] = str(applet_ld["displayName"]) + str("(1)")
        applet_ld["http://www.w3.org/2004/02/skos/core#prefLabel"] = applet_ld[
            "displayName"
        ]
    broken_applet_version = "623ce52a5197b9338bdaf4b6"
    if applet_id == broken_applet_version:
        applet_mongo["meta"]["applet"]["version"] = str("2.6.40")

    broken_conditional_logic = [
        "63ebcec2601cdc0fee1f3d42",
        "63ec1498601cdc0fee1f47d2",
    ]
    if applet_id in broken_conditional_logic:
        for activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            for property in activity["reprolib:terms/addProperties"]:
                if (
                    property["reprolib:terms/isAbout"][0]["@id"]
                    == "IUQ_Wd_Social_Device"
                ):
                    property["reprolib:terms/isVis"] = [{"@value": True}]

    repo_replacements = [
        (
            "mtg137/Stability_tracker_applet_touch",
            "ChildMindInstitute/stability_touch_applet_schema",
        ),
        (
            "mtg137/Stability_tracker_applet",
            "ChildMindInstitute/stability_tilt_applet_schema",
        ),
        (
            "ChildMindInstitute/A-B-Trails",
            "ChildMindInstitute/mindlogger-trails-task",
        ),
    ]
    for what, repl in repo_replacements:
        if "schema:image" in applet_ld and what in applet_ld["schema:image"]:
            contents = json.dumps(applet_ld)
            contents = contents.replace(what, repl)
            applet_ld = json.loads(contents)

    # fix duplicated names for stability activity items in prefLabel
    duplications = [
        (
            "stability_schema",
            [
                "Stability Tracker",
                "Stability tracker instructions",
            ],
        ),
        (
            "flanker_schema",
            [
                "Visual Stimulus Response",
                "Visual Stimulus Response instructions",
            ],
        ),
        (
            "Flanker_360",
            [
                "Visual Stimulus Response",
                "Visual Stimulus Response instructions",
            ],
        ),
    ]
    key = "http://www.w3.org/2004/02/skos/core#prefLabel"
    for stability_activity in applet_ld["reprolib:terms/order"][0]["@list"]:
        for activity_name, item_label in duplications:
            if stability_activity["@id"] == activity_name:
                for stability_item in stability_activity[
                    "reprolib:terms/order"
                ][0]["@list"]:
                    if (
                        key in stability_item
                        and stability_item[key][0]["@value"] in item_label
                    ):
                        stability_item[key][0]["@value"] = (
                            stability_item[key][0]["@value"]
                            + "_"
                            + stability_item["@id"]
                        )

    broken_conditional_logic_naming = [
        "64e7af5e22d81858d681de92",
        "633ecc1ab7ee9765ba54452d",
    ]
    if applet_id in broken_conditional_logic_naming:
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            for _report in _activity["reprolib:terms/reports"][0]["@list"]:
                _report = fix_spacing_in_report(_report)
                if "reprolib:terms/conditionals" in _report:
                    for _conditional in _report["reprolib:terms/conditionals"][
                        0
                    ]["@list"]:
                        _conditional = fix_spacing_in_report(_conditional)

    broken_conditional_non_existing_slider2_item = ["64dce2d622d81858d6819f13"]
    if applet_id in broken_conditional_non_existing_slider2_item:
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            for _report in _activity["reprolib:terms/reports"][0]["@list"]:
                key = "reprolib:terms/printItems"
                if key in _report:
                    _report[key][0]["@list"] = [
                        print_item
                        for print_item in _report[key][0]["@list"]
                        if print_item["@value"] != "Slider2"
                    ]

    broken_conditional_non_existing_items = ["633ecc1ab7ee9765ba54452d"]
    if applet_id in broken_conditional_non_existing_items:
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            if (
                _activity["@id"]
                == "NIH Toolbox: Perceived Stress (SR 18+1) (1)"
            ):
                for _report in _activity["reprolib:terms/reports"][0]["@list"]:
                    key = "reprolib:terms/printItems"
                    if key in _report:
                        _report[key][0]["@list"] = [
                            print_item
                            for print_item in _report[key][0]["@list"]
                            if print_item["@value"]
                            not in [
                                "nihps_sr18_q05",
                                "nihps_sr18_q06",
                                "nihps_sr18_q07",
                                "nihps_sr18_q08",
                            ]
                        ]
                    if _report["@id"] in [
                        "averageScore_score_2",
                        "percentScore_score_3",
                    ]:
                        _report.pop("reprolib:terms/jsExpression")

    duplicated_activity_names = ["640b239b601cdc5212d63e75"]
    key_pref = "http://www.w3.org/2004/02/skos/core#prefLabel"
    key_alt = "http://www.w3.org/2004/02/skos/core#altLabel"
    if applet_id in duplicated_activity_names:
        current_names = []
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            if _activity["@id"] in current_names:
                _activity["@id"] = _activity["@id"] + " (1)"
                _activity[key_pref][0]["@value"] = _activity["@id"]
                _activity[key_alt][0]["@value"] = _activity["@id"]
            current_names.append(_activity["@id"])

    no_ids_flanker_map = {
        "<<<<<": "left-con",
        "<<><<": "right-inc",
        ">><>>": "left-inc",
        ">>>>>": "right-con",
        "--<--": "left-neut",
        "-->--": "right-neut",
    }
    no_ids_flanker_buttons = [
        "62768ff20a62aa1056078093",
        "64946e208819c1120b4f9271",
    ]
    if applet_id in no_ids_flanker_buttons:
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            if _activity["@id"] == "Flanker_360":
                for _item in _activity["reprolib:terms/order"][0]["@list"]:
                    if "reprolib:terms/inputs" in _item:
                        for _intput in _item["reprolib:terms/inputs"]:
                            if "schema:itemListElement" in _intput:
                                for _el in _intput["schema:itemListElement"]:
                                    if (
                                        "@id" not in _el
                                        and "schema:image" in _el
                                    ):
                                        _el["@id"] = no_ids_flanker_map[
                                            _el["schema:image"]
                                        ]
                        _item["reprolib:terms/inputs"].append(
                            {
                                "@type": ["http://schema.org/Text"],
                                "http://schema.org/name": [
                                    {"@language": "en", "@value": "blockType"}
                                ],
                                "http://schema.org/value": [
                                    {"@language": "en", "@value": "practice"}
                                ],
                            }
                        )
                        _item["reprolib:terms/inputs"].append(
                            {
                                "@type": ["http://schema.org/ItemList"],
                                "schema:itemListElement": [
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 1",
                                            }
                                        ],
                                        "schema:value": [{"@value": 0}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 2",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 3",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 4",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                    {
                                        "reprolib:terms/order": [
                                            {
                                                "@list": [
                                                    {"@id": "left-con"},
                                                    {"@id": "right-con"},
                                                    {"@id": "left-inc"},
                                                    {"@id": "right-inc"},
                                                    {"@id": "left-neut"},
                                                    {"@id": "right-neut"},
                                                ]
                                            }
                                        ],
                                        "schema:name": [
                                            {
                                                "@language": "en",
                                                "@value": "Block 5",
                                            }
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                ],
                                "schema:name": [
                                    {"@language": "en", "@value": "blocks"}
                                ],
                                "schema:numberOfItems": [{"@value": 5}],
                            }
                        )
                        _item["reprolib:terms/inputs"].append(
                            {
                                "schema:itemListElement": [
                                    {
                                        "schema:image": "",
                                        "schema:name": [
                                            {"@language": "en", "@value": "<"}
                                        ],
                                        "schema:value": [{"@value": 0}],
                                    },
                                    {
                                        "schema:image": "",
                                        "schema:name": [
                                            {"@language": "en", "@value": ">"}
                                        ],
                                        "schema:value": [{"@value": 1}],
                                    },
                                ],
                                "schema:name": [
                                    {"@language": "en", "@value": "buttons"}
                                ],
                            }
                        )

    applet_ld = patch_prize_activity(applet_id, applet_ld)

    return applet_ld, applet_mongo


def patch_prize_activity(applet_id: str, applet_ld: dict) -> dict:
    # Prize activity
    if applet_id == "613f7a206401599f0e495e0a":
        for _activity in applet_ld["reprolib:terms/order"][0]["@list"]:
            if _activity["@id"] == "PrizeActivity":
                for _item in _activity["reprolib:terms/order"][0]["@list"]:
                    if _item["@id"] == "PrizeSelection":
                        _item["reprolib:terms/inputType"][0][
                            "@value"
                        ] = "radio"

    return applet_ld


def fix_spacing_in_report(_report: dict) -> dict:
    if "@id" in _report:
        _report["@id"] = _report["@id"].replace(" ", "_")
    if "reprolib:terms/isVis" in _report:
        _report["reprolib:terms/isVis"][0]["@value"] = (
            _report["reprolib:terms/isVis"][0]["@value"]
            .replace(
                "averageScore_average_less than",
                "averageScore_average_less_than",
            )
            .replace(
                "averageScore_average_greater than",
                "averageScore_average_greater_than",
            )
            .replace(
                "averageScore_average_equal to",
                "averageScore_average_equal_to",
            )
            .replace(
                "averageScore_average_is not equal to",
                "averageScore_average_is_not_equal_to",
            )
            .replace(
                "averageScore_average_outside of",
                "averageScore_average_outside_of",
            )
        )

    return _report


class Mongo:
    def __init__(self) -> None:
        # Setup MongoDB connection
        # uri = f"mongodb://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}/{os.getenv('MONGO__DB')}"  # noqa: E501
        uri = f"mongodb://{os.getenv('MONGO__HOST')}"  # noqa: E501  {os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@
        self.client = MongoClient(uri, 27017)  # uri
        self.db = self.client[os.getenv("MONGO__DB", "mindlogger")]

    @staticmethod
    async def get_converter_result(schema) -> InternalModel | PublicModel:
        document_loader = get_document_loader()
        context_resolver = get_context_resolver(document_loader)
        converter = get_jsonld_model_converter(
            document_loader, context_resolver
        )

        return await converter.convert(schema)

    def close_connection(self):
        self.client.close()

    def get_users(self) -> list[dict]:
        collection = self.db["user"]
        users = collection.find(
            {},
            {
                "_id": 1,
                "email": 1,
                "firstName": 1,
                "lastName": 1,
                "salt": 1,
                "created": 1,
                "email_encrypted": 1,
            },
        )

        count = 0
        total_documents = 0
        encrypted_count = 0
        results = []
        email_hashes = []

        for user in users:
            first_name = decrypt(user.get("firstName"))
            if not first_name:
                first_name = "-"
            elif len(first_name) >= 50:
                first_name = first_name[:49]
            first_name = enc.process_bind_param(first_name, String)

            last_name = decrypt(user.get("lastName"))
            if not last_name:
                last_name = "-"
            elif len(last_name) >= 50:
                last_name = last_name[:49]
            last_name = enc.process_bind_param(last_name, String)

            if user.get("email"):
                if not user.get("email_encrypted"):
                    email_hash = hashlib.sha224(
                        user.get("email").encode("utf-8")
                    ).hexdigest()
                    if "@" in user.get("email"):
                        email_aes_encrypted = enc.process_bind_param(
                            user.get("email"), String
                        )
                        encrypted_count += 1
                    else:
                        email_aes_encrypted = None
                elif (
                    user.get("email_encrypted")
                    and len(user.get("email")) == 56
                ):
                    email_hash = user.get("email")
                    email_aes_encrypted = None
                else:
                    total_documents += 1
                    continue

                if email_hash not in email_hashes:
                    email_hashes.append(email_hash)
                    results.append(
                        {
                            "id_": user.get("_id"),
                            "email": email_hash,
                            "hashed_password": user.get("salt"),
                            "first_name": first_name,
                            "last_name": last_name,
                            "created_at": user.get("created"),
                            "email_aes_encrypted": email_aes_encrypted,
                        }
                    )
                    count += 1
            total_documents += 1
        print(
            f"Total Users Documents - {total_documents}, "
            f"Successfully prepared for migration - {count}, "
            f"Users with email_aes_encrypted - {encrypted_count}"
        )

        return results

    def get_users_workspaces(self, users_ids: list[ObjectId]) -> list[dict]:
        collection = self.db["accountProfile"]
        users_workspaces = collection.find(
            {
                "$expr": {"$eq": ["$accountId", "$_id"]},
                "userId": {"$in": users_ids},
            }
        )

        count = 0
        results = []

        for user_workspace in users_workspaces:
            workspace_name = user_workspace.get("accountName")
            if len(workspace_name) >= 100:
                workspace_name = workspace_name[:99]
            workspace_name = enc.process_bind_param(workspace_name, String)
            results.append(
                {
                    "id_": user_workspace.get("_id"),
                    "user_id": user_workspace.get("userId"),
                    "workspace_name": workspace_name,
                }
            )
            count += 1
        print(f"Successfully prepared for migration - {count}")

        return results

    def patch_cloned_activities_order(
        self, original_id: ObjectId, applet_format: dict
    ) -> dict:
        """
        This patches a bug in the legacy system where after an applet is duplicated the activities order still
        refers to the original records.
        If it's the case, it will remove those and replace with the cloned applet activities IDs.
        """
        original = Applet().findOne(query={"_id": original_id})
        if original:
            original_format = jsonld_expander.formatLdObject(
                original, "applet", refreshCache=False, reimportFromUrl=False
            )
        else:
            original_format = None

        if (
            original_format
            and "applet" in original_format
            and "reprolib:terms/order" in original_format["applet"]
        ):
            act_blacklist = []
            for _orig_act in original_format["applet"]["reprolib:terms/order"][
                0
            ]["@list"]:
                act_blacklist.append(_orig_act["@id"])

            order = applet_format["applet"]["reprolib:terms/order"][0]["@list"]
            order = [
                _act for _act in order if _act["@id"] not in act_blacklist
            ]
            if len(order) == 0:
                order = [
                    {"@id": str(_act)} for _act in applet_format["activities"]
                ]
            applet_format["applet"]["reprolib:terms/order"][0]["@list"] = order

        return applet_format

    def get_applet_repro_schema(self, applet: dict) -> dict:
        applet_format = jsonld_expander.formatLdObject(
            applet, "applet", refreshCache=False, reimportFromUrl=False
        )

        if applet_format is None or applet_format == {}:
            raise FormatldException(
                message="formatLdObject returned empty object"
            )

        if "duplicateOf" in applet:
            applet_format = self.patch_cloned_activities_order(
                applet["duplicateOf"], applet_format
            )

        if applet_format["activities"] == {}:
            raise FormatldException(
                message="formatLdObject returned empty activities"
            )

        for key, activity in applet_format["activities"].items():
            applet_format["activities"][key] = jsonld_expander.formatLdObject(
                Activity().findOne({"_id": ObjectId(activity)}),
                "activity",
                refreshCache=False,
                reimportFromUrl=False,
            )

        activities_by_id = applet_format["activities"].copy()
        for _key, _activity in activities_by_id.copy().items():
            activity_id = _activity["activity"]["@id"]
            if activity_id not in activities_by_id:
                activities_by_id[activity_id] = _activity.copy()

        # setup activity items
        for key, value in activities_by_id.items():
            if "items" not in value:
                print("Warning: activity  ", key, " has no items")
                continue

            activity_items_by_id = value["items"].copy()
            for _key, _item in activity_items_by_id.copy().items():
                if "url" in _item:
                    activity_items_by_id[_item["url"]] = _item.copy()

            activity_object = value["activity"]
            activity_items_objects = []
            for item in activity_object["reprolib:terms/order"][0]["@list"]:
                item_key = item["@id"]
                if item_key in activity_items_by_id:
                    activity_items_objects.append(
                        activity_items_by_id[item_key]
                    )
                else:
                    activity_items_objects.append(item)
                    print(
                        "Warning: item ",
                        item_key,
                        "presents in order but absent in activity items. activityId:",
                        str(activity_object["_id"]),
                    )

            activities_by_id[key]["activity"]["reprolib:terms/order"][0][
                "@list"
            ] = activity_items_objects
            activities_by_id[key].pop("items")

        applet = applet_format["applet"]
        activity_objects = []
        # setup activities
        for activity in applet["reprolib:terms/order"][0]["@list"]:
            activity_id = self.find_additional_id(
                list(activities_by_id.keys()), activity["@id"]
            )
            if activity_id:
                activity_objects.append(
                    activities_by_id[activity_id]["activity"]
                )
            else:
                print(
                    "Warning: activity ",
                    activity_id,
                    " presents in order but absent in applet activities.",
                )

        applet["reprolib:terms/order"][0]["@list"] = activity_objects

        activity_ids_inside_applet = []
        for activity in activity_objects:
            activity_ids_inside_applet.append(activity["@id"])

        if applet.get("reprolib:terms/activityFlowOrder"):
            activity_flows = applet_format["activityFlows"].copy()
            for _key, _flow in activity_flows.copy().items():
                flow_id = _flow["@id"]
                if flow_id not in activity_flows:
                    activity_flows[flow_id] = _flow.copy()

            activity_flows_fixed = {}
            # setup activity flow items
            for key, activity_flow in activity_flows.items():
                activity_flow_order = []
                for item in activity_flow["reprolib:terms/order"][0]["@list"]:
                    if item["@id"] in activity_ids_inside_applet:
                        activity_flow_order.append(item)
                    else:
                        print(
                            "Warning: item ",
                            item["@id"],
                            "presents in flow order but absent in applet activities. activityFlowId:",
                            str(key),
                        )
                activity_flow["reprolib:terms/order"][0][
                    "@list"
                ] = activity_flow_order
                activity_flows_fixed[key] = activity_flow

            activity_flow_objects = []

            # setup activity flows
            for flow in applet["reprolib:terms/activityFlowOrder"][0]["@list"]:
                if activity_flows_fixed.get(flow["@id"]):
                    activity_flow_objects.append(
                        activity_flows_fixed[flow["@id"]]
                    )

            applet["reprolib:terms/activityFlowOrder"][0][
                "@list"
            ] = activity_flow_objects
        # add context

        applet["@context"] = CONTEXT["@context"]
        applet["@type"] = CONTEXT["@type"]

        return applet

    def find_additional_id(
        self, activities_ids: list[str], activity_id: str
    ) -> str | None:
        if activity_id in activities_ids:
            return activity_id

        lookup = {
            "ab_trails_v1/ab_trails_v1_schema": "A/B Trails v1.0",
            "ab_trails_v2/ab_trails_v2_schema": "A/B Trails v2.0",
            "Flanker/Flanker_schema": "flanker_schema",
            "Stability/Stability_schema": "stability_schema",
        }
        for _a_id in activities_ids:
            for key, value in lookup.items():
                if key in activity_id and value == _a_id:
                    return _a_id

        # e.g take Flanker_schema from
        # https://raw.github.com/CMI/flanker/master/activities/Flanker/Flanker_schema
        activity_id_from_relative_url = activity_id.split("/").pop()
        for _a_id in activities_ids:
            if (
                activity_id_from_relative_url == _a_id
                or activity_id_from_relative_url.lower() == _a_id.lower()
            ):
                return _a_id

        return None

    async def get_applet(self, applet_id: str) -> dict:
        applet = Applet().findOne({"_id": ObjectId(applet_id)})
        if (
            not applet
            or "applet" not in applet["meta"]
            or applet["meta"]["applet"] == {}
        ):
            raise EmptyAppletException()

        ld_request_schema = self.get_applet_repro_schema(applet)
        ld_request_schema, applet = patch_broken_applets(
            applet_id, ld_request_schema, applet
        )
        converted = await self.get_converter_result(ld_request_schema)

        converted.extra_fields["created"] = applet["created"]
        converted.extra_fields["updated"] = applet["updated"]
        converted.extra_fields["version"] = applet["meta"]["applet"].get(
            "version", "0.0.1"
        )
        if "encryption" in applet["meta"]:
            converted.encryption = Encryption(
                public_key=json.dumps(
                    applet["meta"]["encryption"]["appletPublicKey"]
                ),
                prime=json.dumps(applet["meta"]["encryption"]["appletPrime"]),
                base=json.dumps(applet["meta"]["encryption"]["base"]),
                account_id=str(applet["accountId"]),
            )
        converted = self._extract_ids(converted, applet_id)

        return converted

    async def get_applet_versions(self, applet_id: str) -> [dict, str]:
        applet = FolderModel().findOne(query={"_id": ObjectId(applet_id)})
        owner = AccountProfile().findOne(
            query={"applets.owner": {"$in": [ObjectId(applet_id)]}}
        )

        owner_id = owner["userId"] if owner else str(applet["creatorId"])

        protocolId = applet["meta"]["protocol"].get("_id").split("/").pop()
        result = get_versions_from_content(protocolId)
        converted_applet_versions = dict()
        if result is not None and result != {}:
            last_version = list(result.keys())[-1]

            old_activities_by_id = {}
            for version, content in result.items():
                print(version)
                if version == last_version:
                    converted_applet_versions[
                        version
                    ] = {}  # skipping last version for optimization
                else:
                    (
                        ld_request_schema,
                        old_activities_by_id,
                    ) = content_to_jsonld(
                        content["applet"], old_activities_by_id
                    )
                    ld_request_schema = patch_broken_applet_versions(
                        applet_id, ld_request_schema
                    )
                    converted = await self.get_converter_result(
                        ld_request_schema
                    )
                    converted.extra_fields["created"] = content["updated"]
                    converted.extra_fields["updated"] = content["updated"]
                    converted.extra_fields["version"] = version
                    converted = self._extract_ids(converted, applet_id)

                    converted_applet_versions[version] = converted

        return converted_applet_versions, owner_id

    def _extract_ids(self, converted: dict, applet_id: str = None) -> dict:
        converted.extra_fields["id"] = mongoid_to_uuid(
            applet_id
            if applet_id is not None
            else converted.extra_fields["extra"]["_:id"][0]["@value"]
        )
        for activity in converted.activities:
            activity.extra_fields["id"] = mongoid_to_uuid(
                activity.extra_fields["extra"]["_:id"][0]["@value"]
            )
            for item in activity.items:
                item.extra_fields["id"] = mongoid_to_uuid(
                    item.extra_fields["extra"]["_:id"][0]["@value"]
                )
        for flow in converted.activity_flows:
            flow.extra_fields["id"] = mongoid_to_uuid(
                flow.extra_fields["extra"]["_:id"][0]["@value"]
            )
        return converted

    def get_answer_migration_queries(self, **kwargs):
        creator_id_filtering = False
        creator_ids = [ObjectId("64c2395b8819c178d236685a")]

        query = {
            "meta.responses": {"$exists": True},
            "meta.activity.@id": kwargs["activity_id"],
            "meta.applet.@id": kwargs["applet_id"],
            "meta.applet.version": kwargs["version"],
        }
        item_collection = self.db["item"]
        creators_ids = item_collection.find(query).distinct("creatorId")
        result = []
        for creator_id in creators_ids:
            if creator_id_filtering:
                if creator_id not in creator_ids:
                    continue
            result.append({**query, "creatorId": creator_id})

        return result

    def get_answers_with_files(
        self,
        *,
        answer_migration_queries,
    ):
        item_collection = self.db["item"]

        for query in answer_migration_queries:
            items = item_collection.find(query, sort=[("created", ASCENDING)])
            del query["meta.responses"]
            answer_with_files = dict()
            for item in items:
                item = item_collection.find_one({"_id": item["_id"]})
                if not answer_with_files and "dataSource" in item["meta"]:
                    answer_with_files["answer"] = item
                    answer_with_files["query"] = query
                elif answer_with_files and "dataSource" not in item["meta"]:
                    answer_with_files.setdefault("files", []).append(
                        item["meta"]["responses"]
                    )
                elif answer_with_files and "dataSource" in item["meta"]:
                    yield answer_with_files
                    answer_with_files = dict(answer=item, query=query)
            yield answer_with_files

    def get_applet_info(self, applet_id: str) -> dict:
        info = {}
        applet = Applet().findOne({"_id": ObjectId(applet_id)})
        account = AccountProfile().findOne({"_id": applet["accountId"]})
        owner = User().findOne({"_id": applet["creatorId"]})
        info["applet_id"] = applet_id
        info["applet_name"] = applet["meta"]["applet"].get(
            "displayName", "Untitled"
        )
        info["account_name"] = account["accountName"]
        info["owner_email"] = owner["email"]
        info["updated"] = applet["updated"]

        return info

    def docs_by_ids(
        self, collection: str, doc_ids: List[ObjectId]
    ) -> List[dict]:
        return self.db[collection].find({"_id": {"$in": doc_ids}})

    def get_user_nickname(self, user_profile: dict) -> str:
        nick_name = decrypt(user_profile.get("nickName"))
        if not nick_name:
            nick_name = ""
        return nick_name

    def reviewer_meta(
        self, applet_id: ObjectId, account_profile: dict
    ) -> List[uuid.UUID]:
        reviewer_profile = self.db["appletProfile"].find_one(
            {"userId": account_profile["userId"], "appletId": applet_id}
        )
        respondent_profiles = self.db["appletProfile"].find(
            {
                "appletId": applet_id,
                "reviewers": reviewer_profile["_id"],
                "roles": "user",
            }
        )
        user_ids = []
        for profile in respondent_profiles:
            user_id = profile.get("userId")
            if user_id:
                user_ids.append(mongoid_to_uuid(user_id))
        return user_ids

    def respondent_metadata(self, user: dict, applet_id: ObjectId):
        doc_cur = (
            self.db["appletProfile"]
            .find({"userId": user["_id"], "appletId": applet_id})
            .limit(1)
        )
        doc = next(doc_cur, None)
        if not doc:
            return {}
        return {
            "nick": self.get_user_nickname(doc),
            "secret": doc.get("MRN", ""),
        }

    def inviter_id(self, user_id, applet_id):
        doc_invite = self.db["invitation"].find(
            {"userId": user_id, "appletId": applet_id}
        )
        doc_invite = next(doc_invite, {})
        invitor = doc_invite.get("invitedBy", {})
        invitor_profile_id = invitor.get("_id")
        ap_doc = self.db["appletProfile"].find_one({"_id": invitor_profile_id})
        return mongoid_to_uuid(ap_doc["userId"]) if ap_doc else None

    def is_pinned(self, user_id):
        res = self.db["appletProfile"].find_one(
            {"userId": user_id, "pinnedBy": {"$exists": 1, "$ne": []}}
        )
        return bool(res)

    def get_owner_by_applet(self, applet_id: str) -> uuid.UUID | None:
        owner = AccountProfile().findOne(
            query={"applets.owner": {"$in": [ObjectId(applet_id)]}}
        )
        return mongoid_to_uuid(owner["userId"]) if owner else None

    def get_anons(self, anon_id: uuid.UUID) -> List[AppletUserDAO]:
        applet_profiles = self.db["appletProfile"].find(
            {"MRN": "Guest Account Submission"}
        )
        res = []
        for applet_profile in applet_profiles:
            owner_id = self.get_owner_by_applet(applet_profile["appletId"])
            if owner_id is None:
                continue
            res.append(
                AppletUserDAO(
                    applet_id=mongoid_to_uuid(applet_profile["appletId"]),
                    user_id=anon_id,
                    owner_id=owner_id,
                    inviter_id=owner_id,
                    role=Role.RESPONDENT,
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow(),
                    meta={
                        "nickname": "Mindlogger ChildMindInstitute",
                        "secretUserId": "Guest Account Submission",
                    },
                    is_pinned=False,
                    is_deleted=False,
                )
            )
        return res

    def get_user_applet_role_mapping(
        self, migrated_applet_ids: List[ObjectId]
    ) -> List[AppletUserDAO]:
        account_profile_collection = self.db["accountProfile"]
        not_found_users = []
        not_found_applets = []
        access_result = []
        account_profile_docs = account_profile_collection.find()
        for doc in account_profile_docs:
            if doc["userId"] in not_found_users:
                continue

            user = User().findOne({"_id": doc["userId"]})
            if not user:
                continue
            role_applets_mapping = doc.get("applets")
            managerial_applets = []
            for role, applets in role_applets_mapping.items():
                if role != "user":
                    managerial_applets.extend(applets)

            for role_name, applet_ids in role_applets_mapping.items():
                if role_name == Role.OWNER:
                    # Skip owner in case of it was
                    # created on applet migration stage
                    continue
                applet_docs = self.docs_by_ids("folder", applet_ids)
                for applet_id in applet_ids:
                    # Check maybe we already check this id in past
                    if applet_id in not_found_applets:
                        continue

                    if applet_id not in migrated_applet_ids:
                        # Applet doesn't exist in postgresql, just skip it
                        # ant put id to cache
                        continue
                    applet = next(
                        filter(
                            lambda item: item["_id"] == applet_id, applet_docs
                        ),
                        None,
                    )
                    if not applet:
                        continue
                    meta = {}
                    if role_name == Role.REVIEWER:
                        meta["respondents"] = self.reviewer_meta(
                            applet_id, doc
                        )
                    elif role_name == "user":
                        data = self.respondent_metadata(user, applet_id)
                        if data:
                            if applet_id in managerial_applets:
                                if data["nick"] == "":
                                    f_name = decrypt(user["firstName"])
                                    l_name = decrypt(user["lastName"])
                                    meta["nickname"] = (
                                        f"{f_name} {l_name}"
                                        if f_name and l_name
                                        else f"- -"
                                    )
                                else:
                                    meta["nickname"] = data["nick"]

                                meta["secretUserId"] = (
                                    f"{str(uuid.uuid4())}"
                                    if data["secret"] == ""
                                    else data["secret"]
                                )
                            else:
                                meta["nickname"] = data["nick"]
                                meta["secretUserId"] = data["secret"]

                    owner_id = self.get_owner_by_applet(applet_id)
                    if not owner_id:
                        owner_id = mongoid_to_uuid(applet.get("creatorId"))

                    inviter_id = self.inviter_id(doc["userId"], applet_id)
                    if not inviter_id:
                        inviter_id = owner_id
                    access = AppletUserDAO(
                        applet_id=mongoid_to_uuid(applet_id),
                        user_id=mongoid_to_uuid(doc["userId"]),
                        owner_id=owner_id,
                        inviter_id=inviter_id,
                        role=convert_role(role_name),
                        created_at=datetime.datetime.utcnow(),
                        updated_at=datetime.datetime.utcnow(),
                        meta=meta,
                        is_pinned=self.is_pinned(doc["userId"]),
                        is_deleted=False,
                    )
                    access_result.append(access)
        migration_log.warning(
            f"[Role] Prepared for migrations {len(access_result)} items"
        )
        return list(set(access_result))

    def get_pinned_users(self, applets_ids: list[ObjectId] | None):
        query = {
            "pinnedBy": {"$exists": 1},
            "userId": {"$exists": 1, "$ne": None},
        }
        if applets_ids:
            query["appletId"] = {"$in": applets_ids}
        return self.db["appletProfile"].find(query)

    def get_applet_profiles_by_ids(self, ids):
        return self.db["appletProfile"].find({"_id": {"$in": ids}})

    def get_pinned_role(self, applet_profile):
        system_roles = Role.as_list().copy()
        system_roles.remove(Role.RESPONDENT)
        system_roles = set(system_roles)
        applet_roles = set(applet_profile.get("roles", []))
        if system_roles.intersection(applet_roles):
            return Role.MANAGER
        else:
            return Role.RESPONDENT

    def get_owner_by_applet_profile(self, applet_profile):
        profiles = self.db["accountProfile"].find(
            {"userId": applet_profile["userId"]}
        )
        it = filter(lambda p: p["_id"] == p["accountId"], profiles)
        profile = next(it, None)
        return profile["userId"] if profiles else None

    def get_user_pin_mapping(self, applets_ids: list[ObjectId] | None):
        pin_profiles = self.get_pinned_users(applets_ids)
        pin_dao_list = set()
        for profile in pin_profiles:
            if not profile["pinnedBy"]:
                continue
            pinned_by = self.get_applet_profiles_by_ids(profile["pinnedBy"])
            for manager_profile in pinned_by:
                role = self.get_pinned_role(manager_profile)
                owner_id = self.get_owner_by_applet_profile(manager_profile)
                dao = UserPinsDAO(
                    user_id=mongoid_to_uuid(profile["userId"]),
                    pinned_user_id=mongoid_to_uuid(manager_profile["userId"]),
                    owner_id=mongoid_to_uuid(owner_id),
                    role=convert_role(role),
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow(),
                )
                pin_dao_list.add(dao)
        return pin_dao_list

    def get_folders(self, account_id):
        return list(
            FolderModel().find(
                query={"accountId": account_id, "baseParentType": "user"}
            )
        )

    def get_applets_in_folder(self, folder_id):
        return list(
            FolderModel().find(
                query={
                    "baseParentType": "folder",
                    "baseParentId": folder_id,
                    "meta.applet": {"$exists": True},
                }
            )
        )

    def get_root_applets(self, account_id):
        return list(
            FolderModel().find(
                query={
                    "accountId": account_id,
                    "baseParentType": "collection",
                    "baseParentId": ObjectId("5ea689a286d25a5dbb14e82c"),
                    "meta.applet": {"$exists": True},
                }
            )
        )

    def get_folders_and_applets(self, account_id):
        folders = self.get_folders(account_id)
        for folder in folders:
            folder["applets"] = self.get_applets_in_folder(folder["_id"])
        result = {
            "applets": self.get_root_applets(account_id),
            "folders": folders,
        }
        return result

    def get_folder_pin(
        self, folder: dict, applet_id: ObjectId
    ) -> datetime.datetime | None:
        meta = folder.get("meta", {})
        applets_order = meta.get("applets", {})
        order_it = filter(lambda m: m["_id"] == applet_id, applets_order)
        order = next(order_it, None)
        if not order or order.get("_pin_order"):
            return None
        now = datetime.datetime.utcnow()
        return now + datetime.timedelta(seconds=order["_pin_order"])

    def get_folder_mapping(
        self, workspace_ids: List[uuid.UUID]
    ) -> Tuple[Set[FolderDAO], Set[FolderAppletDAO]]:
        folders_list = []
        applets_list = []
        for workspace_id in workspace_ids:
            profile_id = uuid_to_mongoid(workspace_id)
            if profile_id is None:
                # non migrated workspace
                continue
            res = self.get_folders_and_applets(profile_id)
            for folder in res["folders"]:
                folders_list.append(
                    FolderDAO(
                        id=mongoid_to_uuid(folder["_id"]),
                        created_at=folder["created"],
                        updated_at=folder["updated"],
                        name=folder["name"],
                        creator_id=mongoid_to_uuid(folder["creatorId"]),
                        workspace_id=mongoid_to_uuid(folder["parentId"]),
                        migrated_date=datetime.datetime.utcnow(),
                        migrated_update=datetime.datetime.utcnow(),
                        is_deleted=False,
                    )
                )
                for applet in folder["applets"]:
                    pinned_at = self.get_folder_pin(folder, applet["_id"])
                    applets_list.append(
                        FolderAppletDAO(
                            id=uuid.uuid4(),
                            folder_id=mongoid_to_uuid(folder["_id"]),
                            applet_id=mongoid_to_uuid(applet["_id"]),
                            created_at=applet["created"],
                            updated_at=applet["updated"],
                            pinned_at=pinned_at,
                            migrated_date=datetime.datetime.utcnow(),
                            migrated_update=datetime.datetime.utcnow(),
                            is_deleted=False,
                        )
                    )

        return set(folders_list), set(applets_list)

    def get_theme(
        self, key: str | ObjectId, applet_id: uuid.UUID
    ) -> ThemeDao | None:
        if not isinstance(key, ObjectId):
            try:
                theme_id = ObjectId(key)
            except Exception:
                return None
        theme_doc = self.db["folder"].find_one({"_id": theme_id})
        if theme_doc:
            meta = theme_doc.get("meta", {})
            return ThemeDao(
                id=mongoid_to_uuid(theme_doc["_id"]),
                creator_id=mongoid_to_uuid(theme_doc["creatorId"]),
                name=theme_doc["name"],
                logo=meta.get("logo"),
                small_logo=meta.get("smallLogo"),
                background_image=meta.get("backgroundImage"),
                primary_color=meta.get("primaryColor"),
                secondary_color=meta.get("secondaryColor"),
                tertiary_color=meta.get("tertiaryColor"),
                public=theme_doc["public"],
                allow_rename=True,
                created_at=theme_doc["created"],
                updated_at=theme_doc["updated"],
                applet_id=applet_id,
            )
        return None

    def get_library(
        self, applet_ids: list[ObjectId] | None
    ) -> (LibraryDao, ThemeDao):
        lib_set = set()
        theme_set = set()
        query = {}
        if applet_ids:
            query["appletId"] = {"$in": applet_ids}
        library = self.db["appletLibrary"].find(query)
        for lib_doc in library:
            applet_id = mongoid_to_uuid(lib_doc["appletId"])
            version = lib_doc.get("version")
            if version:
                version_id = f"{applet_id}_{version}"
            else:
                version_id = None
            now = datetime.datetime.now()
            created_at = lib_doc.get("createdAt", now)
            updated_at = lib_doc.get("updated_at", now)
            lib = LibraryDao(
                id=mongoid_to_uuid(lib_doc["_id"]),
                applet_id=applet_id,
                applet_id_version=version_id,
                keywords=lib_doc["keywords"],
                search_keywords=lib_doc["keywords"],
                created_at=created_at,
                updated_at=updated_at,
                migrated_date=now,
                migrated_updated=now,
                is_deleted=False,
            )
            theme_id = lib_doc.get("themeId")
            if theme_id:
                theme = self.get_theme(theme_id, applet_id)
                if theme:
                    theme_set.add(theme)
            lib_set.add(lib)
        return lib_set, theme_set

    def get_applets_by_workspace(self, workspace_id: str) -> list[str]:
        items = Profile().find(query={"accountId": ObjectId(workspace_id)})
        ids = set()
        for item in items:
            ids.add(str(item["appletId"]))
        return list(ids)
