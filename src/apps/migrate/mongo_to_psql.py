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


def get_users_from_mongo(db) -> list[dict]:
    collection = db["user"]
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


def save_users_to_postgres(connection, users: list[dict]):
    cursor = connection.cursor()

    for user in users:
        try:
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
        except Exception:
            print(
                "Unable to insert data! "
                f"Key (email)=({user['email']}) already exists!"
            )

    connection.commit()
    cursor.close()


def main():
    # Setup MongoDB connection
    mongo_client = MongoClient("localhost", 27017)
    mongo_db = mongo_client["newdb"]

    # Setup PostgreSQL connection
    postgres_connection = psycopg2.connect(
        host="localhost",
        dbname="mindlogger_backend",
        user="postgres",
        password="postgres",
    )

    # Migrate with users
    users: list[dict] = get_users_from_mongo(mongo_db)
    save_users_to_postgres(postgres_connection, users)

    # TODO: add other migrations there

    # Close connections
    mongo_client.close()
    postgres_connection.close()


if __name__ == "__main__":
    main()
