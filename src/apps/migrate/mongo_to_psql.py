import uuid
from datetime import datetime

import psycopg2  # type: ignore[import]
from Cryptodome.Cipher import AES
from fastapi import FastAPI
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


class Convertor:
    @staticmethod
    def conver_users(users: list[dict]) -> list[dict]:
        """Convert user from mongo into user that can be stored into the Postgres"""
        pass


class Postgres:
    def __init__(self) -> None:
        # Setup PostgreSQL connection
        self.connection = psycopg2.connect(
            host="localhost",
            dbname="mindlogger_backend",
            user="postgres",
            password="postgres",
        )

    def close_connection(self):
        self.connection.close()

    def save_users(self, users: list[dict]) -> dict[str, dict]:
        cursor = self.connection.cursor()

        results: dict[str, dict] = {}

        for user in users:
            try:
                # new_user = cursor.execute(
                cursor.execute(
                    "INSERT INTO users"
                    "(created_at, updated_at, is_deleted, email, hashed_password, "
                    "id, first_name, last_name, last_seen_at)"
                    "VALUES"
                    f"('{user['created_at']}', '{user['updated_at']}', "
                    f"'{user['is_deleted']}', '{user['email']}', "
                    f"'{user['hashed_password']}', '{user['id']}', "
                    f"'{user['first_name']}', '{user['last_name']}', "
                    f"'{user['last_seen_at']}');"
                )

                # TODO: Check this
                # results[user["id"]] = new_user

            except Exception:
                print(
                    "Unable to insert data! "
                    f"Key (email)=({user['email']}) already exists!"
                )

        self.connection.commit()
        cursor.close()

        # ------------------------------------
        # Return the users mapping
        # {"<old_user_id>": {<new_user_object>}}
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # TODO: Return new users mapping from postgres
        return results

    def save_applets(
        self, users_mapping: dict[str, dict], applets: list[dict]
    ):
        pass

    def save_activities(self, activities: list[dict])
        """Returns the mapping between old activity ID and the created activity.

        {
            17: {id: 6, value: {}}
        }
        Where 17 is a old id and the object on the right side is a new created object in the database
        """

        # TODO
        return {}

    def save_activity_items(self, items: list[dict], activity_mapping: dict[str, dict]):
        """
        items = [
            {id: 1, activity_id: 17, data: {}}
            {id: 2, activity_id: 131, data: {}}
        ]

        mapping = {
            17: {id: 6, value: {}}
        }

        for item in items:
            created_activity: dict = mapping[iteam['activity_id']]
            payload = {
                'activity_id': created_activity['id']
            }
        """
        pass


class Mongo:
    def __init__(self) -> None:
        # Setup MongoDB connection
        self.client = MongoClient("localhost", 27017)
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


def main():
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    users: list[dict] = mongo.get_users()
    new_users_mapping: dict[str, dict] = postgres.save_users(users)

    # Migrate with activities
    activities: list[dict] = mongo.get_activities()
    new_activities_mapping: dict[str, dict] = postgres.save_activities(activities)

    # Migrate with activity items
    items: list[dict] = mongo.get_items()
    created_items = postgres.save_activity_items(items, new_activities_mapping)

    # TODO: Migrate wiht applets
    # applets: list[dict] = mongo.get_applets()
    # postgres.save_applets(new_users_mapping, applets)

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    main()
