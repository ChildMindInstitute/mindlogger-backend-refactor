__all__ = ["UserDeviceEventsHistoryCRUD"]

import datetime
import uuid

from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from apps.schedule.db.schemas import UserDeviceEventsHistorySchema
from infrastructure.database import BaseCRUD


class UserDeviceEventsHistoryCRUD(BaseCRUD[UserDeviceEventsHistorySchema]):
    async def record_event_versions(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        event_versions: list[tuple[uuid.UUID, str]],
    ) -> list[UserDeviceEventsHistorySchema]:
        values = [
            dict(
                user_id=user_id,
                device_id=device_id,
                event_id=event_id,
                version=event_version,
            )
            for event_id, event_version in event_versions
        ]

        upsert: Insert = pg_insert(UserDeviceEventsHistorySchema)
        upsert = upsert.values(values)
        upsert = upsert.on_conflict_do_update(
            constraint=UserDeviceEventsHistorySchema.unique_constraint,
            set_={
                "updated_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            },
        )
        upsert = upsert.returning(UserDeviceEventsHistorySchema)
        result = await self._execute(upsert)

        rows = result.mappings().all()
        model = [UserDeviceEventsHistorySchema(**row) for row in rows]

        return model
