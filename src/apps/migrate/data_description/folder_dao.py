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
