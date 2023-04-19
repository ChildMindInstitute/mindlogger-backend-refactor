import uuid
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
    except Exception:
        return None

    txt = plaintext.decode("utf-8")
    length = int(txt[-max_count:])

    return txt[:length]


class Mongo:
    def __init__(self) -> None:
        # Setup MongoDB connection
        self.client = MongoClient("localhost", 27017)  # type: ignore
        self.db = self.client["newdb"]

    def close_connection(self):
        self.client.close()

    def get_users(self) -> list[dict]:
        collection = self.db["user"]
        users = collection.find(
            {}, {"email": 1, "firstName": 1, "lastName": 1, "salt": 1}
        )

        count = 0
        results = []

        for user in users:
            first_name = decrypt(user.get("firstName"))
            if not first_name:
                first_name = "-"
            elif len(first_name) > 50:
                first_name = first_name[:50]

            last_name = decrypt(user.get("lastName"))
            if not last_name:
                last_name = "-"
            elif len(last_name) > 50:
                last_name = last_name[:50]

            if user.get("email"):
                results.append(
                    {
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                        "is_deleted": False,
                        "email": user.get("email"),
                        "hashed_password": user.get("salt"),
                        "id": uuid.uuid4(),
                        "first_name": first_name,
                        "last_name": last_name,
                        "last_seen_at": datetime.now(),
                    }
                )
                count += 1
            # break
        print("!!! count =", count)

        return results

    def get_applets(self) -> list[dict]:
        # TODO
        return []

    def get_activities(self) -> list[dict]:
        # TODO
        return []

    def get_items(self) -> list[dict]:
        # TODO
        return []
