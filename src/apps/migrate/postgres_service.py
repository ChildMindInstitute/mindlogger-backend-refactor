import uuid
from contextlib import suppress
from datetime import datetime

import psycopg2  # type: ignore[import]


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
        """Returns the mapping between old Users ID and the created Users.

        {
            ObjectId('5ea689...14e806'):
            {
                'id': UUID('f96014b9-...-4239f959e07e'),
                'created_at': datetime(2023, 4, 20, 2, 51, 9, 860661),
                'updated_at': datetime(2023, 4, 20, 2, 51, 9, 860665),
                'is_deleted': False,
                'email': 'avocado7989@gmail.com',
                'hashed_password': '$2b$12$Y.../PO',
                'first_name': 'firstname',
                'last_name': '-',
                'last_seen_at': datetime(2023, 4, 20, 2, 51, 9, 860667)
            }
        }
        Where ObjectId('5ea689...14e806') is the old '_id'
        and a new object created in the Postgres database
        """

        cursor = self.connection.cursor()

        results: dict[str, dict] = {}
        count = 0

        for old_user in users:
            time_now = datetime.now()
            new_user = {
                "id": uuid.uuid4(),
                "created_at": time_now,
                "updated_at": time_now,
                "last_seen_at": time_now,
                "is_deleted": False,
                "email": old_user["email"],
                "hashed_password": old_user["hashed_password"],
                "first_name": old_user["first_name"],
                "last_name": old_user["last_name"],
            }
            with suppress(Exception):
                cursor.execute(
                    "INSERT INTO users"
                    "(created_at, updated_at, is_deleted, email, "
                    "hashed_password, id, first_name, last_name, "
                    "last_seen_at)"
                    "VALUES"
                    f"('{new_user['created_at']}', '{new_user['updated_at']}', "
                    f"'{new_user['is_deleted']}', '{new_user['email']}', "
                    f"'{new_user['hashed_password']}', '{new_user['id']}', "
                    f"'{new_user['first_name']}', '{new_user['last_name']}', "
                    f"'{new_user['last_seen_at']}');"
                )

                results[old_user["id_"]] = new_user
                count += 1

        self.connection.commit()
        cursor.close()

        print(f"Errors in {len(users) - count} users")
        print(f"Successfully migrated {count} users")

        return results

    def save_users_workspace(
        self, users_mapping: dict[str, dict]
    ) -> list[dict]:

        cursor = self.connection.cursor()

        results: list[dict] = []
        count = 0

        for user in users_mapping.values():
            time_now = datetime.now()

            # Create users workspace
            user_workspace = {
                "id": uuid.uuid4(),
                "created_at": time_now,
                "updated_at": time_now,
                "is_deleted": False,
                "user_id": user["id"],
                "workspace_name": f"{user['first_name']} "
                f"{user['last_name']}",
                "is_modified": False,
            }

            with suppress(Exception):
                cursor.execute(
                    "INSERT INTO users_workspaces"
                    "(user_id, id, created_at, updated_at, is_deleted, "
                    "workspace_name, is_modified)"
                    "VALUES"
                    f"((SELECT id FROM users WHERE id = '{user['id']}'), "
                    f"'{user_workspace['id']}', "
                    f"'{user_workspace['created_at']}', "
                    f"'{user_workspace['updated_at']}', "
                    f"'{user_workspace['is_deleted']}', "
                    f"'{user_workspace['workspace_name']}', "
                    f"'{user_workspace['is_modified']}');"
                )

                results.append(user_workspace)
                count += 1

        self.connection.commit()
        cursor.close()

        print(f"Errors in {len(users_mapping) - count} users_workspace")
        print(f"Successfully migrated {count} users_workspace")

        return results

    def save_applets(
        self, users_mapping: dict[str, dict], applets: list[dict]
    ):
        pass

    def save_activities(self, activities: list[dict]):
        """Returns the mapping between old activity ID and the created activity.

        {
            17: {id: 6, value: {}}
        }
        Where 17 is a old id and the object on the right side
        is a new created object in the database
        """

        # TODO
        return {}

    def save_activity_items(
        self, items: list[dict], activity_mapping: dict[str, dict]
    ):
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
