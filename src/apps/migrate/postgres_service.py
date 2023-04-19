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
        cursor = self.connection.cursor()

        results: dict[str, dict] = {}

        for user in users:
            try:
                # new_user = cursor.execute(
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
