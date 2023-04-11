import uuid
from datetime import datetime
from Cryptodome.Cipher import AES

import psycopg2  # type: ignore[import]
from fastapi import FastAPI
from pymongo import MongoClient


def decrypt(data):
    aes_key = b"n]fwen%Z.,Ce4!/0(1D-Q0#ZUOBoqJrV"
    max_count = 4
    try:
        cipher = AES.new(aes_key, AES.MODE_EAX, nonce=data[-32:-16])
        plaintext = cipher.decrypt(data[:-32])
        cipher.verify(data[-16:])

        txt = plaintext.decode("utf-8")
        length = int(txt[-max_count:])
    except:
        return None

    return txt[:length]


def create_app():
    """Create the app"""
    _app = FastAPI(
        description="Migrate mongo to psql",
    )

    # Mongodb connection options
    db_name = "newdb"
    host = "localhost"
    port = 27017

    # Connection to Mongodb
    client = MongoClient(host, port)

    db = client[db_name]

    collection = db["user"]
    users = collection.find(
        {}, {"email": 1, "firstName": 1, "lastName": 1, "salt": 1}
    ).limit(5)
    count = 0
    users_list = []
    for user in users:
        count += 1

        last_name = user.get("lastName")
        if last_name:
            last_name = decrypt(last_name)
        else:
            last_name = "-"

        users_list.append(
            {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_deleted": False,
                "email": user.get("email"),
                "hashed_password": user.get("salt"),
                "id": uuid.uuid4(),
                "first_name": decrypt(user.get("firstName")),
                "last_name": last_name,
                "last_seen_at": datetime.now(),
            }
        )

    # Close Mongodb connection
    client.close()

    # Connection to Postgresql
    conn = psycopg2.connect(
        host="localhost",
        dbname="mindlogger_backend",
        user="postgres",
        password="postgres",
    )

    cursor = conn.cursor()

    for user in users_list:
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

    conn.commit()
    cursor.close()
    conn.close()

    return _app


app = create_app()
