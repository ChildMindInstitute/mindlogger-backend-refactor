import datetime
import uuid
from dataclasses import dataclass


@dataclass
class FolderDAO:
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool
    name: str
    creator_id: uuid.UUID
    workspace_id: uuid.UUID
    migrated_date: datetime.datetime
    migrated_update: datetime.datetime

    def __hash__(self):
        return hash(self.id)

    def __str__(self) -> str:
        values = ",".join(
            [
                f"'{self.id}'::UUID",
                f"'{self.created_at}'::TIMESTAMP",
                f"'{self.updated_at}'::TIMESTAMP",
                f"{self.is_deleted}",
                f"'{self.name}'",
                f"'{self.creator_id}'::UUID",
                f"'{self.workspace_id}'::UUID",
                f"'{self.migrated_date}'::TIMESTAMP",
                f"'{self.migrated_update}'::TIMESTAMP",
            ]
        )
        return """
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
            VALUES ({values})
        """.format(
            values=values
        )


@dataclass
class FolderAppletDAO:
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool
    folder_id: uuid.UUID
    applet_id: uuid.UUID
    pinned_at: datetime.datetime | None
    migrated_date: datetime.datetime
    migrated_update: datetime.datetime

    def __hash__(self):
        return hash((self.folder_id, self.applet_id))

    def __str__(self) -> str:
        values = ",".join(
            [
                f"'{self.id}'::UUID",
                f"'{self.created_at}'::TIMESTAMP",
                f"'{self.updated_at}'::TIMESTAMP",
                f"{self.is_deleted}",
                f"'{self.folder_id}'::UUID",
                f"'{self.applet_id}'::UUID",
                f"{self.pinned_at if self.pinned_at else 'NULL'}",
                f"'{self.migrated_date}'::TIMESTAMP",
                f"'{self.migrated_update}'::TIMESTAMP",
            ]
        )
        return """
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
            VALUES ({values})
        """.format(
            values=values
        )
