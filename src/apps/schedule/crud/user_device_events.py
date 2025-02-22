__all__ = ["UserDeviceEventsCRUD"]

import datetime
import uuid

from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from apps.schedule.db.schemas import UserDeviceEventsSchema
from infrastructure.database import BaseCRUD


class UserDeviceEventsCRUD(BaseCRUD[UserDeviceEventsSchema]):
    async def record_event_versions(
        self,
        device_id: uuid.UUID,
        event_versions: list[tuple[uuid.UUID, str]],
    ) -> list[UserDeviceEventsSchema]:
        values = [
            dict(
                device_id=device_id,
                event_id=event_id,
                version=event_version,
            )
            for event_id, event_version in event_versions
        ]

        upsert: Insert = pg_insert(UserDeviceEventsSchema)
        upsert = upsert.values(values)
        upsert = upsert.on_conflict_do_update(
            constraint=UserDeviceEventsSchema.unique_constraint,
            set_={
                "updated_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            },
        )
        upsert = upsert.returning(UserDeviceEventsSchema)
        result = await self._execute(upsert)

        rows = result.mappings().all()
        model = [UserDeviceEventsSchema(**row) for row in rows]

        return model
