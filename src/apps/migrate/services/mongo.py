import asyncio
import json
from pprint import pprint as print
from typing import Any

from bson.objectid import ObjectId
from Cryptodome.Cipher import AES
from pymongo import MongoClient

# from apps.applets.domain.applet_create_update import AppletCreate

from apps.girderformindlogger.utility import jsonld_expander
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)
from apps.shared.domain.base import InternalModel, PublicModel
from config import settings


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
        self.client = MongoClient("mongo", 27017)  # type: ignore # "localhost"
        self.db = self.client["mindlogger"]

    @staticmethod
    async def get_converter_result(schema) -> InternalModel | PublicModel:
        document_loader = get_document_loader()
        context_resolver = get_context_resolver(document_loader)
        converter = get_jsonld_model_converter(
            document_loader, context_resolver
        )

        return await (converter.convert(schema))

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
        collection = self.db["folder"]
        cache  =self.db["cache"]
        # NOTE: All applets have baseParentId 5ea689a286d25a5dbb14e82c
        applets = collection.find_one(
            {"_id": ObjectId("63f5f9aded51ea1c1e6dff69")},
            # {"parentId": ObjectId("5ea689a086d25a5dbb14e808")},
        )

        # applet_cache = json.loads(cache.find_one({"_id":applets["cached"]})["cache_data"])

        applet_format = jsonld_expander.formatLdObject(applets, "applet")

        print(applet_format)



        # TODO: Remove limit after testing

        results: list[Any] = []
        # for applet in applets:
        #     ld_request_schema = self.get_applet_repro_schema(applet)
        #     converter_result = await self.get_converter_result(
        #         ld_request_schema
        #     )

        #     results.append(converter_result)

        return results
