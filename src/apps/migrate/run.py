from apps.migrate.mongo_service import Mongo
from apps.migrate.postgres_service import Postgres

# class Convertor:
#     @staticmethod
#     def conver_users(users: list[dict]) -> list[dict]:
#         """Convert user from mongo into user
#         that can be stored into the Postgres"""
#         pass


def main():
    mongo = Mongo()
    postgres = Postgres()

    # Migrate with users
    users: list[dict] = mongo.get_users()
    postgres.save_users(users)

    # TODO: Migrate with applets
    # applets: list[dict] = mongo.get_applets()
    # postgres.save_applets(new_users_mapping, applets)

    # TODO: Migrate with activities
    # activities: list[dict] = mongo.get_activities()
    # new_activities_mapping: dict[str, dict] = postgres.save_activities(
    #     activities
    # )

    # TODO: Migrate with activity items
    # items: list[dict] = mongo.get_items()
    # created_items = postgres.save_activity_items(
    #     items, new_activities_mapping
    # )

    # Close connections
    mongo.close_connection()
    postgres.close_connection()


if __name__ == "__main__":
    main()
