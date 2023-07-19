# import asyncio
import json
from pprint import pprint as print
from typing import Any

from bson.objectid import ObjectId
from Cryptodome.Cipher import AES
from pymongo import MongoClient

from apps.girderformindlogger.models.activity import Activity
from apps.girderformindlogger.models.applet import Applet
from apps.girderformindlogger.utility import jsonld_expander
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)
from apps.shared.domain.base import InternalModel, PublicModel
from config import settings

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
        self.client = MongoClient("mongo", 27017)  # "localhost"
        self.db = self.client["mindlogger"]

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
            },
        )

        count = 0
        total_documents = 0
        results = []

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
                results.append(
                    {
                        "id_": user.get("_id"),
                        "email": user.get("email"),
                        "hashed_password": user.get("salt"),
                        "first_name": first_name,
                        "last_name": last_name,
                    }
                )
                count += 1
            total_documents += 1
        print(
            f"Total Users Documents - {total_documents}, "
            f"Successfully prepared for migration - {count}"
        )

        return results

    def get_applet_repro_schema(self, applet: dict) -> dict:
        with open(settings.apps_dir / "migrate/repro_template.json") as file:
            data = json.load(file)

            # TODO: Fill the template with applet data
            return data

    async def get_applets(self) -> list[dict]:
        # collection = self.db["folder"]
        # cache = self.db["cache"]

        # NOTE: All applets have baseParentId 5ea689a286d25a5dbb14e82c
        # applets = collection.find_one(
        #     {"_id": ObjectId("63f5f9aded51ea1c1e6dff69")},
        #     # {"parentId": ObjectId("5ea689a086d25a5dbb14e808")},
        # )

        # TODO: divide formatting to json-ld into functions(activities(activity items), flows)  # noqa: E501

        applets = Applet().findOne(
            {"_id": ObjectId("62d15a03154fa87efa129760")}
        )
        # applet_cache = json.loads(cache.find_one({"_id":applets["cached"]})["cache_data"])  # noqa: E501

        applet_format = jsonld_expander.formatLdObject(applets, "applet")
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

        # ld_request_schema = self.get_applet_repro_schema(applet)
        converter_result = await self.get_converter_result(applet)
        print(converter_result.dict().keys())

        # print(applet["reprolib:terms/order"][0]["@list"][0]["reprolib:terms/order"][0]["@list"][0].keys())

        # TODO: Remove limit after testing

        results: list[Any] = []
        # for applet in applets:
        #     ld_request_schema = self.get_applet_repro_schema(applet)
        #     converter_result = await self.get_converter_result(
        #         ld_request_schema
        #     )

        #     results.append(converter_result)

        return results
