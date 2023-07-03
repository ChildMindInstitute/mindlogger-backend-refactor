import asyncio
from pprint import pprint as print

import requests
from bson.objectid import ObjectId
from Cryptodome.Cipher import AES
from pymongo import MongoClient

from apps.applets.domain.applet_create_update import AppletCreate
from apps.jsonld_converter.dependencies import (
    get_context_resolver,
    get_document_loader,
    get_jsonld_model_converter,
)


def decrypt(data):
    aes_key = b"n]fwen%Z.,Ce4!/0(1D-Q0#ZUOBoqJrV"
    max_count = 4

    try:
        cipher = AES.new(aes_key, AES.MODE_EAX, nonce=data[-32:-16])
        plaintext = cipher.decrypt(data[:-32])
        cipher.verify(data[-16:])
    except Exception as error:
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
    #                 "reprolib": "https://raw.githubusercontent.com/ReproNim/reproschema/master/"
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

    def get_applets(self) -> list[dict]:
        collection = self.db["folder"]
        # NOTE: All applets have baseParentId 5ea689a286d25a5dbb14e82c
        applets = [
            dict(el)
            for el in collection.find(
                {"baseParentId": ObjectId("5ea689a286d25a5dbb14e82c")},
            ).limit(100)
        ]

        # NOTE: All applets have baseParentId 5ea689a086d25a5dbb14e80a
        # activities = [
        #     dict(el)
        #     for el in collection.find(
        #         {"baseParentId": ObjectId("5ea689a086d25a5dbb14e80a")},
        #     ).limit(100)
        # ]

        # Temporary
        results: list[dict] = []
        for applet in applets:
            # temporary variable
            # ld_request_schema = _get_applet_ld_schema(applet[])

            # TODO: Fetch all applet activities...

            # Create the create activity payload
            # payload = applet | {
            #     "displayName": applet["name"],
            #     # NOTE: ASK ABOUT WHERE SHOULD WE TAKE THE APPLET PASSWORD
            #     "password": "",
            #     # TODO: Fetch activities by this applet and add the loop within the loop
            #     "activities": [],
            #     # TODO: Fetch activity flows by this applet and add the loop within the loop
            #     "activityFlows": [],
            # }
            document_loader = get_document_loader()
            context_resolver = get_context_resolver(document_loader)
            converter = get_jsonld_model_converter(
                document_loader, context_resolver
            )

            # protocol = asyncio.run(converter.convert(response.json()))
            applet_create_schema = asyncio.run(converter.convert(dict(applet)))
            breakpoint()

            results.append(applet_create_schema.dict())

        return results

        # response = requests.get(element["meta"]["protocol"]["url"])

        # if response.status_code == 404:
        #     print("404!!!")
        #     return []

        # document_loader = get_document_loader()
        # context_resolver = get_context_resolver(document_loader)
        # converter = get_jsonld_model_converter(
        #     document_loader, context_resolver
        # )

        # # protocol = asyncio.run(converter.convert(response.json()))
        # applet_create_schema = asyncio.run(converter.convert(template))

        # breakpoint()

        # return []

    def get_activities(self) -> list[dict]:
        # TODO
        return []

    def get_items(self) -> list[dict]:
        # TODO
        return []
