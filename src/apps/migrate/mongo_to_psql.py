import uuid
from datetime import datetime

import psycopg2  # type: ignore[import]
from fastapi import FastAPI
from pymongo import MongoClient


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

        # If you want to decrypt values during migration
        # you need the AES_KEY.
        # And you should use something similar to this:
        # pipenv install --dev pycryptodomex == 3.9.7
        # from Cryptodome.Cipher import AES
        #
        # def decrypt(self, data):
        #     try:
        #         cipher = AES.new(
        #               self.AES_KEY, AES.MODE_EAX, nonce=data[-32:-16]
        #         )
        #         plaintext = cipher.decrypt(data[:-32])
        #         cipher.verify(data[-16:])
        #
        #         txt = plaintext.decode('utf-8')
        #         length = int(txt[-self.maxCount:])
        #
        #         return ('ok', txt[:length])
        #     except:
        #         return ('error', None)

        users_list.append(
            {
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_deleted": False,
                "email": user.get("email"),
                "hashed_password": user.get("salt"),
                "id": uuid.uuid4(),
                "first_name": user.get("firstName"),
                "last_name": user.get("lastName"),
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
