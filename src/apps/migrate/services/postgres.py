import os
import uuid
from contextlib import suppress
from datetime import datetime
from typing import List

import psycopg2
from bson import ObjectId

from apps.migrate.services.applet_service import AppletMigrationService
from apps.migrate.utilities import mongoid_to_uuid, uuid_to_mongoid
from infrastructure.database import session_manager
from infrastructure.database import atomic
from apps.migrate.data_description.applet_user_access import AppletUserDAO


class Postgres:
    def __init__(self) -> None:
        # Setup PostgreSQL connection
        self.connection = psycopg2.connect(
            host=os.getenv("DATABASE__HOST", "postgres"),
            port=os.getenv("DATABASE__PORT", "5432"),
            dbname=os.getenv("DATABASE__DB", "mindlogger_backend"),
            user=os.getenv("DATABASE__USER", "postgres"),
            password=os.getenv("DATABASE__PASSWORD", "postgres"),
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
                'email': '3400...031d',
                'email_aes_encrypted': 'b'6X\xb4\x12...\xf6\xed'' | null
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
                "id": mongoid_to_uuid(old_user["id_"]),
                "created_at": old_user["created_at"],
                "updated_at": time_now,
                "last_seen_at": time_now,
                "is_deleted": False,
                "email": old_user["email"],
                "hashed_password": old_user["hashed_password"],
                "first_name": old_user["first_name"],
                "last_name": old_user["last_name"],
                "email_aes_encrypted": old_user["email_aes_encrypted"],
            }
            with suppress(Exception):
                cursor.execute(
                    "INSERT INTO users"
                    "(created_at, updated_at, is_deleted, email, "
                    "hashed_password, id, first_name, last_name, "
                    "last_seen_at, email_aes_encrypted)"
                    "VALUES"
                    f"('{new_user['created_at']}', "
                    f"'{new_user['updated_at']}', "
                    f"'{new_user['is_deleted']}', '{new_user['email']}', "
                    f"'{new_user['hashed_password']}', '{new_user['id']}', "
                    f"'{new_user['first_name']}', '{new_user['last_name']}', "
                    f"'{new_user['last_seen_at']}', "
                    f"'{new_user['email_aes_encrypted']}');"
                )

                results[old_user["id_"]] = new_user
                count += 1

        self.connection.commit()
        cursor.close()

        print(f"Errors in {len(users) - count} users")
        print(f"Successfully migrated {count} users")

        return results

    def save_users_workspace(
        self, workspaces: list[dict], users_mapping: dict[str, dict]
    ) -> list[dict]:
        cursor = self.connection.cursor()

        results: list[dict] = []
        count = 0

        for workspace in workspaces:
            time_now = datetime.now()
            # Create users workspace
            user_workspace = {
                "id": mongoid_to_uuid(workspace["id_"]),
                "created_at": time_now,
                "updated_at": time_now,
                "is_deleted": False,
                "user_id": users_mapping[workspace["user_id"]]["id"],
                "workspace_name": workspace["workspace_name"].replace(
                    "'", "''"
                )
                if "'" in workspace["workspace_name"]
                else workspace["workspace_name"],
                "is_modified": False,
            }

            with suppress(Exception):
                cursor.execute(
                    "INSERT INTO users_workspaces"
                    "(user_id, id, created_at, updated_at, is_deleted, "
                    "workspace_name, is_modified)"
                    "VALUES"
                    f"((SELECT id FROM users WHERE id = '{user_workspace['user_id']}'), "  # noqa: E501
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
        print(f"Errors in {len(workspaces) - count} users_workspace")
        print(f"Successfully migrated {count} users_workspace")
        return results

    # def save_applets(
    #     self, users_mapping: dict[str, dict], applets: list[dict]
    # ):
    #     pass

    async def save_applets(
        self,
        applets_by_versions: dict,
        owner_id: str,
    ):
        owner_uuid = mongoid_to_uuid(owner_id)
        initail_version = list(applets_by_versions.keys())[0]
        # applet = applets_by_versions[version]
        session = session_manager.get_session()

        # print(applets_by_versions)

        # print("mongo uuid", applet.extra_fields["id"])

        # TODO: Lookup the owner_uuid for the applet workspace

        async with atomic(session):
            for version, applet in applets_by_versions.items():
                if version == initail_version:
                    applet_create = await AppletMigrationService(
                        session, owner_uuid
                    ).create(applet, owner_uuid)
                else:
                    applet_create = await AppletMigrationService(
                        session, owner_uuid
                    ).update(applet)
                    # break

        # print(applet_create)

        # for applet in applets:
        #     applet_dict = dict(applet)

        #     # NOTE: Not finished ...
        #     session = session_manager.get_session()

        #     applet_created = await AppletService(session, owner_uuid).create(
        #         AppletCreate(
        #             activities=applet_dict.get("activities"),
        #             activity_flows=applet_dict.get("activity_flows"),
        #             display_name=applet_dict.get("display_name"),
        #             encryption={
        #                 "public_key": "",
        #                 "prime": "",
        #                 "base": "",
        #                 "account_id": "",
        #             },
        #             # NOTE: extra_fields=applet_dict.get("activities"),
        #         ),
        #         owner_uuid,
        #     )
        #     print(applet_created)

        # {
        #     "applet_uuid": [
        #         {
        #             "mongo_version": "1.0.0",
        #             "postgres_version": "1.1.0",
        #         }
        #     ]
        # }

    def get_migrated_applets(self) -> list[ObjectId]:
        sql = 'SELECT id FROM "applets"'
        cursor = self.connection.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        app_map = map(lambda t: uuid_to_mongoid(uuid.UUID(t[0])), results)
        return list(filter(lambda app: app is not None, app_map))

    def get_migrated_users_ids(self):
        sql = 'SELECT id FROM "users"'
        cursor = self.connection.cursor()
        cursor.execute(sql)
        user = cursor.fetchone()
        while user:
            yield uuid_to_mongoid(uuid.UUID(user[0]))
            user = cursor.fetchone()
        cursor.close()

    async def save_user_access_workspace(
        self, access_mapping: List[AppletUserDAO]
    ):
        page = 1
        size = 100
        cursor = self.connection.cursor()
        start = (page - 1) * size
        end = page * size
        chunk = access_mapping[start:end]

        while chunk:
            values = [str(c) for c in chunk]
            values = ",".join(values)
            sql = f"""
            INSERT INTO user_applet_accesses
            (
                "id", 
                "created_at", 
                "updated_at", 
                "is_deleted", 
                "role", 
                "user_id", 
                "applet_id",
                "owner_id",
                "invitor_id",
                "meta",
                "is_pinned",
                "migrated_date",
                "migrated_updated"
            )
            VALUES {values}
            """

            cursor.execute(sql)
            page += 1
            start = (page - 1) * size
            end = page * size
            chunk = access_mapping[start:end]
            print("Migrated", page * size)
        self.connection.commit()
        cursor.close()
