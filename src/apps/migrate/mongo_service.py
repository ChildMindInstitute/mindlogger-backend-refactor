from datetime import datetime

from Cryptodome.Cipher import AES
from pymongo import MongoClient


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

    def get_applets(self) -> list[dict]:
        collection = self.db["folder"]

        folders = collection.find()
        for folder in folders:
            if str(folder.get("_id")) == "5ef14aa5cf98a62237946010":
                print(folder)

        # folder = collection.find(
        #     {'_id': '5ef14aa5cf98a62237946010'}
        # )

        # folder = collection.find(
        #     {},
        #     {
        #         "_id": 1, "name": 1, "description": 1,
        #         "parentCollection": 1, "baseParentId": 1
        #     },
        # )
        return []

    def get_activities(self) -> list[dict]:
        # TODO
        return []

    def get_items(self) -> list[dict]:
        # TODO
        return []
