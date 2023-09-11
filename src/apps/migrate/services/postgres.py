import logging

import math
import os
import uuid
from contextlib import suppress
from datetime import datetime
from typing import List, Collection, Any

import psycopg2
from psycopg2.errorcodes import UNIQUE_VIOLATION, FOREIGN_KEY_VIOLATION
from bson import ObjectId

from apps.migrate.data_description.folder_dao import FolderDAO, FolderAppletDAO
from apps.migrate.data_description.library_dao import LibraryDao, ThemeDao
from apps.migrate.services.applet_service import AppletMigrationService
from apps.migrate.utilities import (
    mongoid_to_uuid,
    uuid_to_mongoid,
    migration_log,
)
from infrastructure.database import session_manager
from infrastructure.database import atomic
from apps.migrate.data_description.applet_user_access import AppletUserDAO
from apps.migrate.data_description.user_pins import UserPinsDAO


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

    def wipe_applet(self, applet_id: ObjectId|uuid.UUID|str):
        if isinstance(applet_id, ObjectId):
            applet_id = mongoid_to_uuid(str(applet_id))
        if isinstance(applet_id, str) and len(applet_id) == 24:
            applet_id = mongoid_to_uuid(applet_id)
        if isinstance(applet_id, str) and len(applet_id) == 36:
            applet_id = uuid.UUID(applet_id)


        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM flow_item_histories WHERE id IN (SELECT id FROM flow_items WHERE activity_id IN (SELECT id FROM activities WHERE applet_id = %s))", (applet_id.hex,))
        cursor.execute("DELETE FROM flow_items WHERE activity_id IN (SELECT id FROM activities WHERE applet_id = %s)", (applet_id.hex,))
        cursor.execute("DELETE FROM activities WHERE applet_id = %s", (applet_id.hex,))
        cursor.execute("DELETE FROM user_applet_accesses WHERE applet_id = %s", (applet_id.hex,))
        cursor.execute("DELETE FROM flow_histories WHERE applet_id LIKE %s", (str(applet_id)+'%',))
        cursor.execute("DELETE FROM activity_histories WHERE applet_id LIKE %s", (str(applet_id)+'%',))
        cursor.execute("DELETE FROM applet_histories WHERE id = %s", (applet_id.hex,))
        cursor.execute("DELETE FROM flows WHERE applet_id = %s", (applet_id.hex,))
        cursor.execute("DELETE FROM applets WHERE id = %s", (applet_id.hex,))

        self.connection.commit()
        cursor.close()

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
                'email_encrypted': '3653b319e9...b69b7e3e748' | null
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
            time_now = datetime.utcnow()
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
                "email_encrypted": old_user["email_aes_encrypted"],
            }
            try:
                sql = """
                    INSERT INTO users
                    (created_at, updated_at, is_deleted, email, 
                    hashed_password, id, first_name, last_name,
                    last_seen_at, email_encrypted,
                    migrated_date, migrated_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    sql,
                    (
                        str(new_user['created_at']),
                        str(new_user['updated_at']),
                        new_user['is_deleted'],
                        new_user['email'],
                        new_user['hashed_password'],
                        str(new_user['id']),
                        new_user['first_name'],
                        new_user['last_name'],
                        str(new_user['last_seen_at']),
                        new_user['email_encrypted'],
                        str(time_now),
                        str(time_now),
                    ),
                )

                results[old_user["id_"]] = new_user
                count += 1

            except Exception as e:
                print(f"Error: {e}")
                self.connection.rollback()

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
            time_now = datetime.utcnow()
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

            try:
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
            except Exception as e:
                print(f"Error: {e}")
                self.connection.rollback()

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
        last_version = list(applets_by_versions.keys())[-1]
        # applet = applets_by_versions[version]
        session = session_manager.get_session()

        # print(applets_by_versions)

        # print("mongo uuid", applet.extra_fields["id"])

        # TODO: Lookup the owner_uuid for the applet workspace

        async with atomic(session):
            service = AppletMigrationService(session, owner_uuid)

            applet = applets_by_versions[last_version]
            applet_name = await service.get_unique_name(applet.display_name)

            for version, applet in applets_by_versions.items():
                applet.display_name = applet_name
                if version == initail_version:
                    applet_create = await service.create(applet, owner_uuid)
                else:
                    applet_create = await service.update(applet)
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

    def get_pk_array(self, sql, as_bson=True) -> List[uuid.UUID | ObjectId]:
        cursor = self.connection.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        if as_bson:
            m = map(lambda t: uuid_to_mongoid(uuid.UUID(t[0])), results)
        else:
            m = map(lambda t: uuid.UUID(t[0]), results)
        return list(filter(lambda i: i is not None, m))

    def get_migrated_applets(self) -> list[ObjectId]:
        return self.get_pk_array('SELECT id FROM "applets"')

    def get_migrated_users_ids(self):
        return self.get_pk_array('SELECT id FROM "users"', as_bson=False)

    def insert_dao_collection(self, sql, dao_collection: List[Any]):
        size = 1000
        cursor = self.connection.cursor()
        chunk_count = math.ceil(len(dao_collection) / size)
        inserted_count = 0
        for chunk_num in range(chunk_count):
            start = chunk_num * size
            end = (chunk_num + 1) * size
            chunk_values = dao_collection[start:end]
            values = [str(item) for item in chunk_values]
            values_rows = ",".join(values)
            sql_literals = sql.format(values=values_rows)
            cursor.execute(sql_literals)
            inserted_count += cursor.rowcount
        self.connection.commit()
        cursor.close()
        return inserted_count

    def save_user_access_workspace(self, access_mapping: List[AppletUserDAO]):
        sql = """
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
        for row in access_mapping:
            cursor = self.connection.cursor()
            query = sql.format(values=str(row))
            try:
                cursor.execute(query)
            except Exception as ex:
                if not hasattr(ex, "pgcode"):
                    # not pg error
                    raise ex
                if getattr(ex, "pgcode") == UNIQUE_VIOLATION:
                    migration_log.warning(f"Role already exist {row=}")
                else:
                    raise ex
            self.connection.commit()

    def save_user_pins(self, user_pin_dao):
        sql = """
            INSERT INTO user_pins
            (
                id, 
                is_deleted, 
                user_id, 
                pinned_user_id, 
                owner_id, 
                "role", 
                created_at, 
                updated_at, 
                migrated_date, 
                migrated_updated
            )
            VALUES {values}
        """
        rows_count = self.insert_dao_collection(sql, list(user_pin_dao))
        migration_log.warning(f"Inserted {rows_count} rows")

    def get_migrated_workspaces(self) -> List[uuid.UUID]:
        sql = "SELECT id FROM users_workspaces"
        return self.get_pk_array(sql, as_bson=False)

    def log_pg_err(self, ex):
        if not hasattr(ex, "pgcode"):
            # not pg error
            raise ex
        if getattr(ex, "pgcode") == FOREIGN_KEY_VIOLATION:
            migration_log.warning(f"[FOLDERS] {ex}")
        elif getattr(ex, "pgcode") == UNIQUE_VIOLATION:
            migration_log.warning(f"[FOLDERS] {ex}")
        else:
            raise ex

    def save_folders(self, folders: List[FolderDAO]):
        sql = """
            INSERT INTO folders
            (
                id, 
                created_at, 
                updated_at, 
                is_deleted, 
                name, 
                creator_id, 
                workspace_id, 
                migrated_date, 
                migrated_updated
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        migrated, skipped = 0, 0
        for folder_data in folders:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    sql,
                    (
                        str(folder_data.id),
                        folder_data.created_at,
                        folder_data.updated_at,
                        folder_data.is_deleted,
                        folder_data.name,
                        str(folder_data.creator_id),
                        str(folder_data.workspace_id),
                        folder_data.migrated_date,
                        folder_data.migrated_update,
                    ),
                )
                migrated += 1
            except Exception as ex:
                skipped += 1
                self.log_pg_err(ex)
            finally:
                self.connection.commit()
        return migrated, skipped

    def save_folders_applet(self, folder_applets: List[FolderAppletDAO]):
        migrated, skipped = 0, 0
        sql = """
            INSERT INTO public.folder_applets
            (
                id, 
                created_at, 
                updated_at, 
                is_deleted, 
                folder_id, 
                applet_id, 
                pinned_at, 
                migrated_date, 
                migrated_updated
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)

        """
        for folder_applet in folder_applets:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    sql,
                    (
                        str(folder_applet.id),
                        folder_applet.created_at,
                        folder_applet.updated_at,
                        folder_applet.is_deleted,
                        str(folder_applet.folder_id),
                        str(folder_applet.applet_id),
                        folder_applet.pinned_at,
                        folder_applet.migrated_date,
                        folder_applet.migrated_update,
                    ),
                )
                migrated += 1
            except Exception as ex:
                skipped += 1
                self.log_pg_err(ex)
            finally:
                self.connection.commit()
        return migrated, skipped

    def exec_escaped(self, sql: str, values: tuple, log_tag=""):
        success = False
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, values)
            success = True
        except Exception as ex:
            migration_log.warning(f"{log_tag} {ex}")
        finally:
            self.connection.commit()
        return success

    def save_library_item(self, lib: LibraryDao) -> bool:
        sql = """
        INSERT INTO public."library"
        (
            id,  
            is_deleted,
            applet_id_version, 
            keywords, 
            search_keywords, 
            created_at, 
            updated_at, 
            migrated_date, 
            migrated_updated
        )
        VALUES(
            %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.exec_escaped(sql, lib.values(), "[LIBRARY]")

    def save_theme_item(self, theme: ThemeDao) -> bool:
        sql = """
            INSERT INTO public.themes
            (
                id,
                creator_id,
                created_at, 
                updated_at, 
                is_deleted, 
                "name", 
                logo, 
                background_image, 
                primary_color, 
                secondary_color, 
                tertiary_color, 
                public, 
                allow_rename, 
                migrated_date, 
                migrated_updated
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        return self.exec_escaped(sql, theme.values(), "[THEME]")

    def get_latest_applet_id_version(self, applet_id: uuid.UUID) -> str | None:
        sql = """
            SELECT id_version 
            FROM applet_histories 
            WHERE id = %s 
            ORDER BY id_version desc 
            LIMIT 1
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, (str(applet_id),))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_applet_library_keywords(
        self, applet_id: uuid.UUID, applet_version: str
    ) -> List[str]:
        kw = []
        cursor = self.connection.cursor()
        sql = "SELECT description FROM applets WHERE id=%s"
        cursor.execute(sql, (str(applet_id),))
        result = cursor.fetchone()
        if result and result[0]:
            kw.extend(result[0].values())
        sql = "SELECT name FROM activity_histories where applet_id=%s"
        cursor.execute(sql, (applet_version,))
        result = cursor.fetchall()
        act_names = map(lambda row: row[0], result)
        kw.extend(act_names)
        return kw

    def add_theme_to_applet(self, applet_id: uuid.UUID, theme_id: uuid.UUID):
        sql = "UPDATE applets SET theme_id = %s WHERE id = %s"
        return self.exec_escaped(
            sql, (str(theme_id), str(applet_id)), "[THEME APPLET]"
        )
