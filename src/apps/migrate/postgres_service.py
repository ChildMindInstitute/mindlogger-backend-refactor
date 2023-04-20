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

        for user in users:
            try:
                cursor.execute(
                    "INSERT INTO users"
                    "(created_at, updated_at, is_deleted, email, "
                    "hashed_password, id, first_name, last_name, "
                    "last_seen_at)"
                    "VALUES"
                    f"('{user['created_at']}', '{user['updated_at']}', "
                    f"'{user['is_deleted']}', '{user['email']}', "
                    f"'{user['hashed_password']}', '{user['id']}', "
                    f"'{user['first_name']}', '{user['last_name']}', "
                    f"'{user['last_seen_at']}');"
                )

                new_user = {
                    "id": user["id"],
                    "created_at": user["created_at"],
                    "updated_at": user["updated_at"],
                    "is_deleted": user["is_deleted"],
                    "email": user["email"],
                    "hashed_password": user["hashed_password"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "last_seen_at": user["last_seen_at"],
                }

                results[user["_id"]] = new_user

            except Exception:
                print(
                    "Unable to insert data! "
                    f"Key (email)=({user['email']}) already exists!"
                )

        self.connection.commit()
        cursor.close()

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
