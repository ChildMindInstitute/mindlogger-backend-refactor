import datetime
import hashlib
import os
import uuid
from typing import List, Set, Tuple
import json

from Cryptodome.Cipher import AES
from bson.objectid import ObjectId
from pymongo import MongoClient

from apps.girderformindlogger.models.activity import Activity
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.models.account_profile import AccountProfile
from apps.girderformindlogger.models.user import User

from apps.girderformindlogger.models.folder import Folder as FolderModel
from apps.girderformindlogger.models.user import User
from apps.girderformindlogger.utility import jsonld_expander
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)
from apps.migrate.data_description.applet_user_access import AppletUserDAO
from apps.migrate.data_description.user_pins import UserPinsDAO
from apps.migrate.data_description.folder_dao import FolderDAO, FolderAppletDAO
from apps.migrate.exception.exception import (
    FormatldException,
    EmptyAppletException,
)
from apps.migrate.services.applet_versions import (
    get_versions_from_content,
    content_to_jsonld,
    CONTEXT,
)
from apps.migrate.utilities import (
    mongoid_to_uuid,
    migration_log,
    convert_role,
    uuid_to_mongoid,
)
from apps.shared.domain.base import InternalModel, PublicModel
from apps.shared.encryption import encrypt
from apps.workspaces.domain.constants import Role
from apps.applets.domain.base import Encryption


def decrypt(data):
    aes_key = b"n]fwen%Z.,Ce4!/0(1D-Q0#ZUOBoqJrV"
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


def patch_broken_applet_versions(applet_id: str, applet: dict) -> dict:
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
        for activity in applet["reprolib:terms/order"][0]["@list"]:
            for property in activity["reprolib:terms/addProperties"]:
                property["reprolib:terms/isVis"] = [{"@value": True}]

    return applet


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
    return applet_ld, applet_mongo


class Mongo:
    def __init__(self) -> None:
        # Setup MongoDB connection
        # uri = f"mongodb+srv://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}"  # noqa: E501
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

            last_name = decrypt(user.get("lastName"))
            if not last_name:
                last_name = "-"
            elif len(last_name) >= 50:
                last_name = last_name[:49]

            if user.get("email"):
                if not user.get("email_encrypted"):
                    email_hash = hashlib.sha224(
                        user.get("email").encode("utf-8")
                    ).hexdigest()
                    if "@" in user.get("email"):
                        email_aes_encrypted = encrypt(
                            bytes(user.get("email"), "utf-8")
                        ).hex()
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

    def get_applet_repro_schema(self, applet: dict) -> dict:
        applet_format = jsonld_expander.formatLdObject(
            applet, "applet", refreshCache=False, reimportFromUrl=False
        )

        if applet_format is None or applet_format == {}:
            raise FormatldException(
                message="formatLdObject returned empty object"
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
            activity_id = activity["@id"]
            if activity_id in activities_by_id:
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

    async def get_applet(self, applet_id: str) -> dict:
        applet = Applet().findOne({"_id": ObjectId(applet_id)})
        if "applet" not in applet["meta"] or applet["meta"]["applet"] == {}:
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
        owner_id = str(applet["creatorId"])
        protocolId = applet["meta"]["protocol"].get("_id").split("/").pop()
        result = get_versions_from_content(protocolId)
        converted_applet_versions = dict()
        if result is not None:
            old_activities_by_id = {}
            for version, content in result.items():
                print(version)
                ld_request_schema, old_activities_by_id = content_to_jsonld(
                    content["applet"], old_activities_by_id
                )
                ld_request_schema = patch_broken_applet_versions(
                    applet_id, ld_request_schema
                )
                converted = await self.get_converter_result(ld_request_schema)
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

    def get_user_nickname(self, user) -> str:
        first_name = decrypt(user.get("firstName"))
        if not first_name:
            first_name = "-"
        elif len(first_name) >= 50:
            first_name = first_name[:49]

        last_name = decrypt(user.get("lastName"))
        if not last_name:
            last_name = "-"
        elif len(last_name) >= 50:
            last_name = last_name[:49]
        return f"{first_name} {last_name}"

    def reviewer_meta(self, applet_id: ObjectId) -> List[str]:
        applet_docs = self.db["accountProfile"].find(
            {"applets.user": applet_id}
        )
        return list(
            map(lambda doc: str(mongoid_to_uuid(doc["userId"])), applet_docs)
        )

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
            "nick": self.get_user_nickname(user),
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
                msg = (
                    f"Skip AppletProfile({doc['_id']}), "
                    f"User({doc['userId']}) does not exist (field: userId)"
                )
                migration_log.warning(msg)
                not_found_users.append(doc["userId"])
                continue
            role_applets_mapping = doc.get("applets")
            for role_name, applet_ids in role_applets_mapping.items():
                applet_docs = self.docs_by_ids("folder", applet_ids)
                for applet_id in applet_ids:
                    # Check maybe we already check this id in past
                    if applet_id in not_found_applets:
                        continue

                    if applet_id not in migrated_applet_ids:
                        # Applet doesn't exist in postgresql, just skip it
                        # ant put id to cache
                        migration_log.warning(
                            f"Skip: Applet({applet_id}) "
                            f"doesnt represent in PostgreSQL"
                        )
                        not_found_applets.append(applet_id)
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
                        meta["respondents"] = self.reviewer_meta(applet_id)
                    elif role_name == "user":
                        data = self.respondent_metadata(user, applet_id)
                        if data:
                            meta["nickname"] = data["nick"]
                            meta["secretUserId"] = data["secret"]

                    owner_id = (
                        mongoid_to_uuid(applet.get("creatorId"))
                        if applet.get("creatorId")
                        else None
                    )
                    access = AppletUserDAO(
                        applet_id=mongoid_to_uuid(applet_id),
                        user_id=mongoid_to_uuid(doc["userId"]),
                        owner_id=owner_id,
                        inviter_id=self.inviter_id(doc["userId"], applet_id),
                        role=convert_role(role_name),
                        created_at=datetime.datetime.now(),
                        updated_at=datetime.datetime.now(),
                        meta=meta,
                        is_pinned=self.is_pinned(doc["userId"]),
                        is_deleted=False,
                    )
                    access_result.append(access)
        migration_log.warning(
            f"[Role] Prepared for migrations {len(access_result)} items"
        )
        return list(set(access_result))

    def get_pinned_users(self):
        return self.db["appletProfile"].find(
            {"pinnedBy": {"$exists": 1}, "userId": {"$exists": 1, "$ne": None}}
        )

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

    def get_user_pin_mapping(self):
        pin_profiles = self.get_pinned_users()
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
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
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
        now = datetime.datetime.now()
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
                        migrated_date=datetime.datetime.now(),
                        migrated_update=datetime.datetime.now(),
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
                            migrated_date=datetime.datetime.now(),
                            migrated_update=datetime.datetime.now(),
                            is_deleted=False,
                        )
                    )

        return set(folders_list), set(applets_list)
