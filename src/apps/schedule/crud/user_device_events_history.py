__all__ = ["UserDeviceEventsHistoryCRUD"]

import datetime
import uuid

from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Query
from sqlalchemy.sql.expression import select

from apps.schedule.db.schemas import UserDeviceEventsHistorySchema
from apps.shared.query_params import QueryParams
from infrastructure.database import BaseCRUD


class UserDeviceEventsHistoryCRUD(BaseCRUD[UserDeviceEventsHistorySchema]):
    def __init__(self, session):
        super().__init__(session)
        self.schema_class = UserDeviceEventsHistorySchema

    async def get_device(
        self,
        device_id: str,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        event_version: str,
    ) -> UserDeviceEventsHistorySchema:
        query: Query = select(UserDeviceEventsHistorySchema)
        query = query.where(UserDeviceEventsHistorySchema.device_id == device_id)
        query = query.where(UserDeviceEventsHistorySchema.user_id == user_id)
        query = query.where(UserDeviceEventsHistorySchema.event_id == event_id)
        query = query.where(UserDeviceEventsHistorySchema.event_version == event_version)

        result = await self._execute(query)
        return result.scalars().first()

    async def record_event_versions(
        self,
        user_id: uuid.UUID,
        device_id: str,
        event_versions: list[tuple[uuid.UUID, str]],
        os_name: str | None = None,
        os_version: str | None = None,
        app_version: str | None = None,
    ) -> list[UserDeviceEventsHistorySchema]:
        values = [
            dict(
                user_id=user_id,
                device_id=device_id,
                event_id=event_id,
                event_version=event_version,
                os_name=os_name,
                os_version=os_version,
                app_version=app_version,
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

    async def get_all_by_device_id(self, device_id: str) -> list[UserDeviceEventsHistorySchema]:
        query: Query = select(UserDeviceEventsHistorySchema)
        query = query.where(UserDeviceEventsHistorySchema.device_id == device_id)
        result = await self._execute(query)
        return result.scalars().all()

    async def get_all(self) -> list[UserDeviceEventsHistorySchema]:
        return await self._all()

    async def retrieve_applet_all_device_events_history(self, applet_id: uuid.UUID, query_params: QueryParams):
        pass
