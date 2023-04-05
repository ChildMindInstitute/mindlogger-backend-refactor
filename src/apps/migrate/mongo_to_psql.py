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
    # documents = collection.find()
    # for document in documents:
    #     print(document)

    user = collection.find_one(
        {"email": "qwer@fn.com"}, {"_id": 1, "email": 1, "firstName": 1}
    )

    print("user", user)
    print("user.get('email')", user.get("email"))
    print("user.get('firstName')", user.get("firstName"))
    first_name = user.get("firstName")
    print("first_name", first_name)
    # Close connection
    client.close()

    return _app


app = create_app()
