import hashlib
import os
from pprint import pprint as print
from typing import Any

from bson.objectid import ObjectId
from Cryptodome.Cipher import AES
from pymongo import MongoClient

from apps.girderformindlogger.models.activity import Activity
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.models.folder import Folder as FolderModel
from apps.girderformindlogger.utility import jsonld_expander
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)
from apps.migrate.services.applet_versions import (
    get_versions_from_content,
    content_to_jsonld,
)
from apps.shared.domain.base import InternalModel, PublicModel

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
        uri = f"mongodb+srv://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}"  # noqa: E501
        print(uri)
        self.client = MongoClient("mongo", 27017)
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
                elif (
                    user.get("email_encrypted")
                    and len(user.get("email")) == 56
                ):
                    email_hash = user.get("email")
                else:
                    total_documents += 1
                    continue

                if email_hash not in email_hashes:
                    email_hashes.append(email_hash)
                    results.append(
                        {
                            "id_": user.get("_id"),
                            "email": user.get("email"),
                            "email_hash": email_hash,
                            "hashed_password": user.get("salt"),
                            "first_name": first_name,
                            "last_name": last_name,
                            "created_at": user.get("created"),
                        }
                    )
                    count += 1
            total_documents += 1
        print(
            f"Total Users Documents - {total_documents}, "
            f"Successfully prepared for migration - {count}"
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
        applet_format = jsonld_expander.formatLdObject(applet, "applet")

        for key, activity in applet_format["activities"].items():
            applet_format["activities"][key] = jsonld_expander.formatLdObject(
                Activity().findOne({"_id": activity}), "activity"
            )

        activities = applet_format["activities"]
        # setup activity items
        for key, value in activities.items():
            activity_items = value["items"]
            activity_object = value["activity"]
            activity_items_objects = []
            for item in activity_object["reprolib:terms/order"][0]["@list"]:
                activity_items_objects.append(activity_items[item["@id"]])

            activities[key]["activity"]["reprolib:terms/order"][0][
                "@list"
            ] = activity_items_objects
            activities[key].pop("items")

        applet = applet_format["applet"]
        activity_objects = []
        # setup activities
        for activity in applet["reprolib:terms/order"][0]["@list"]:
            activity_objects.append(activities[activity["@id"]]["activity"])

        applet["reprolib:terms/order"][0]["@list"] = activity_objects

        activity_flows = applet_format["activityFlows"]
        activity_flow_objects = []
        # setup activity flows
        for flow in applet["reprolib:terms/activityFlowOrder"][0]["@list"]:
            activity_flow_objects.append(activity_flows[flow["@id"]])

        applet["reprolib:terms/activityFlowOrder"][0][
            "@list"
        ] = activity_flow_objects
        # add context

        context = {
            "@context": [
                {
                    "reprolib": "https://raw.githubusercontent.com/ReproNim/reproschema/master/"  # noqa: E501
                },
                "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json",  # noqa: E501
            ],
            "@type": "https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/Protocol",  # noqa: E501
        }

        applet["@context"] = context["@context"]
        applet["@type"] = context["@type"]

        return applet

    async def get_applets(self) -> list[dict]:
        # NOTE: All applets have baseParentId 5ea689a286d25a5dbb14e82c

        applet = Applet().findOne(
            {"_id": ObjectId("62d15a03154fa87efa129760")}
        )
        ld_request_schema = self.get_applet_repro_schema(applet)
        converter_result = await self.get_converter_result(ld_request_schema)
        print(converter_result.dict().keys())

        results: list[Any] = []

        # for applet in applets:
        #     ld_request_schema = self.get_applet_repro_schema(applet)
        #     converter_result = await self.get_converter_result(
        #         ld_request_schema
        #     )

        #     results.append(converter_result)

        return results

    async def get_applet_versions(self, applet_id: str) -> [dict, str]:
        applet = FolderModel().findOne(query={"_id": ObjectId(applet_id)})
        owner_id = str(applet["creatorId"])
        protocolId = applet["meta"]["protocol"].get("_id").split("/").pop()
        result = get_versions_from_content(protocolId)
        converted_applet_versions = dict()
        for version, content in result.items():
            print(version)
            ld_request_schema = content_to_jsonld(content["applet"])
            converted_applet_versions[
                version
            ] = await self.get_converter_result(ld_request_schema)

        return converted_applet_versions, owner_id
