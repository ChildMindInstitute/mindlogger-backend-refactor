import datetime
import hashlib
import os
from typing import List

from Cryptodome.Cipher import AES
from bson.objectid import ObjectId
from pymongo import MongoClient

from apps.girderformindlogger.models.activity import Activity
from apps.girderformindlogger.models.applet import Applet
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
from apps.migrate.exception.exception import (
    FormatldException,
    EmptyAppletException,
)
from apps.migrate.services.applet_versions import (
    get_versions_from_content,
    content_to_jsonld,
    CONTEXT,
)
from apps.migrate.utilities import mongoid_to_uuid
from apps.shared.domain.base import InternalModel, PublicModel
from apps.shared.encryption import encrypt
from apps.workspaces.domain.constants import Role


# from apps.applets.domain.applet_create_update import AppletCreate


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


class Mongo:
    def __init__(self) -> None:
        # Setup MongoDB connection
        # uri = f"mongodb+srv://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}"  # noqa: E501
        # uri = f"mongodb://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}"  # noqa: E501
        self.client = MongoClient("mongo", 27017)  # uri
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
            activity_flows = applet_format["activityFlows"]
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
                activity_flow_objects.append(activity_flows_fixed[flow["@id"]])

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
        converted = await self.get_converter_result(ld_request_schema)

        converted.extra_fields["created"] = applet["created"]
        converted.extra_fields["updated"] = applet["updated"]
        converted.extra_fields["version"] = applet["meta"]["applet"].get(
            "version", "0.0.1"
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
            for version, content in result.items():
                print(version)
                ld_request_schema = content_to_jsonld(content["applet"])
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
            {"userId": user_id, "pinnedBy": {"$exists": 1}}
        )
        return bool(res)

    def get_user_applet_role_mapping(
        self, migrated_applet_ids: List[ObjectId]
    ) -> List[AppletUserDAO]:
        account_profile_collection = self.db["accountProfile"]
        not_found_users = []
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
                print(msg)
                not_found_users.append(doc["userId"])
                continue
            role_applets_mapping = doc.get("applets")
            for role_name, applet_ids in role_applets_mapping.items():
                applet_docs = self.docs_by_ids("folder", applet_ids)
                for applet_id in applet_ids:
                    if applet_id not in migrated_applet_ids:
                        print(
                            f"Skip: Applet({applet_id}) "
                            f"doesnt represent in PostgreSQL"
                        )
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
                        role=role_name,
                        created_at=datetime.datetime.now(),
                        updated_at=datetime.datetime.now(),
                        meta=meta,
                        is_pinned=self.is_pinned(doc["userId"]),
                        is_deleted=False,
                    )
                    access_result.append(access)
        print("Prepared for migrations", len(access_result))
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
                    role=role,
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                )
                pin_dao_list.add(dao)
        return pin_dao_list
