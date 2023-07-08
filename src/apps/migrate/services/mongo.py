import asyncio
import json
from pprint import pprint as print
from typing import Any

from bson.objectid import ObjectId
from Cryptodome.Cipher import AES
from pymongo import MongoClient

# from apps.applets.domain.applet_create_update import AppletCreate
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
        self.client = MongoClient("localhost", 27017)  # type: ignore
        self.db = self.client["mindlogger"]

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

    # @staticmethod
    # def _get_applet_ld_schema(
    #     applet_id: str, ld_id: str, applet_name: str
    # ) -> dict:
    #     return {
    #         "@context": [
    #             "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json",
    #             {
    #                 "reprolib":
    #                 "https://raw.githubusercontent.com/ReproNim/reproschema/master/"
    #             },
    #         ],
    #         "@type": "reproschema:Protocol",
    #         "@id": ld_id,
    #         "appletName": applet_name,
    #         "prefLabel": {"en": "Protocol1", "es": "Protocol1_es"},
    #         "description": "example Protocol",
    #         "schemaVersion": "1.0.0-rc2",
    #         "version": "0.0.1",
    #         "landingPage": [{"@id": "README.md", "inLanguage": "en"}],
    #         "name": "/mindlogger-demo_schema (373)",
    #         "parentCollection": "collection",
    #         "baseParentId": "5ea689a286d25a5dbb14e82c",
    #         "baseParentType": "collection",
    #         "parentId": "5ea689a286d25a5dbb14e82c",
    #         "creatorId": "5ef14941cf98a6223794600e",
    #         "_id": applet_id,
    #     }

    def get_applet_repro_schema(self, applet: dict) -> dict:
        with open(settings.apps_dir / "migrate/repro_template.json") as file:
            data = json.load(file)
            # TODO: Fill the template with applet data
            return data

    async def get_applets(self) -> list[dict]:
        collection = self.db["folder"]
        # NOTE: All applets have baseParentId 5ea689a286d25a5dbb14e82c
        applets = collection.find(
            {"baseParentId": ObjectId("5ea689a086d25a5dbb14e808")},
        ).limit(2)

        results: list[Any] = []
        for applet in applets:
            ld_request_schema = self.get_applet_repro_schema(applet)

            document_loader = get_document_loader()
            context_resolver = get_context_resolver(document_loader)
            converter = get_jsonld_model_converter(
                document_loader, context_resolver
            )

            create_schema: InternalModel | PublicModel = await (
                converter.convert(ld_request_schema)
            )
            # breakpoint()
            results.append(create_schema)

        return results

    def get_activities(self) -> list[dict]:
        # TODO
        return []

    def get_items(self) -> list[dict]:
        # TODO
        return []
