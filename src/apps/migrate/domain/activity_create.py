import datetime
import uuid

from apps.activities.domain.activity_create import PreparedActivityItemCreate


class ActivityItemMigratedCreate(PreparedActivityItemCreate):
    id: uuid.UUID
    created_at: datetime.date
    updated_at: datetime.date
    migrated_date: datetime.date
    migrated_updated: datetime.date
