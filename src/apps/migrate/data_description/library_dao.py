import datetime
import uuid
from dataclasses import dataclass
from typing import List


@dataclass
class LibraryDao:
    id: uuid.UUID
    applet_id: uuid.UUID
    applet_id_version: str | None
    keywords: List[str]
    search_keywords: List[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    migrated_date: datetime.datetime
    migrated_updated: datetime.datetime
    is_deleted: bool = False

    def __hash__(self):
        return self.id.int

    def __eq__(self, other):
        return hash(other) == hash(self)

    def values(self) -> tuple:
        return (
            str(self.id),
            self.is_deleted,
            self.applet_id_version,
            self.keywords,
            self.search_keywords,
            self.created_at,
            self.updated_at,
            self.migrated_date,
            self.migrated_updated,
        )


@dataclass
class ThemeDao:
    id: uuid.UUID
    creator_id: uuid.UUID
    applet_id: uuid.UUID
    name: str
    logo: str | None
    small_logo: str | None
    background_image: str | None
    primary_color: str
    secondary_color: str
    tertiary_color: str
    public: bool
    allow_rename: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    migrated_date: datetime.datetime = datetime.datetime.utcnow()
    migrated_updated: datetime.datetime = datetime.datetime.utcnow()
    is_deleted: bool = False

    def __hash__(self):
        return self.id.int

    def __eq__(self, other):
        return hash(other) == hash(self)

    def values(self):
        return (
            str(self.id),
            str(self.creator_id),
            self.created_at,
            self.updated_at,
            self.is_deleted,
            self.name,
            self.logo,
            self.small_logo,
            self.background_image,
            self.primary_color,
            self.secondary_color,
            self.tertiary_color,
            self.public,
            self.allow_rename,
            self.migrated_date,
            self.migrated_updated,
        )
