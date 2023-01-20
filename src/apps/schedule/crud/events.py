from apps.schedule.db.schemas import (
    ActivityEventsSchema,
    EventSchema,
    FlowEventsSchema,
    UserEventsSchema,
)
from infrastructure.database import BaseCRUD

__all__ = [
    "EventCRUD",
    "UserEventsCRUD",
    "ActivityEventsCRUD",
    "FlowEventsCRUD",
]


class EventCRUD(BaseCRUD[EventSchema]):
    schema_class = EventSchema

    async def get_by_id(self, id: int) -> EventSchema:
        pass

    async def get_by_user_id(self, user_id: int) -> EventSchema:
        pass

    async def get_by_activity_id(self, activity_id: int) -> EventSchema:
        pass

    async def get_by_flow_id(self, flow_id: int) -> EventSchema:
        pass

    async def save(self, schema: EventSchema) -> EventSchema:
        pass

    async def update(self, schema: EventSchema) -> EventSchema:
        pass

    async def delete(self, id: int) -> EventSchema:
        pass


class UserEventsCRUD(BaseCRUD[UserEventsSchema]):
    async def create(self, schema: UserEventsSchema) -> UserEventsSchema:
        pass

    async def retrieve(self, id: int) -> UserEventsSchema:
        pass

    async def update(self, schema: UserEventsSchema) -> UserEventsSchema:
        pass

    async def delete(self, id: int) -> UserEventsSchema:
        pass


class ActivityEventsCRUD(BaseCRUD[ActivityEventsSchema]):
    async def create(
        self, schema: ActivityEventsSchema
    ) -> ActivityEventsSchema:
        pass

    async def retrieve(self, id: int) -> ActivityEventsSchema:
        pass

    async def update(
        self, schema: ActivityEventsSchema
    ) -> ActivityEventsSchema:
        pass

    async def delete(self, id: int) -> ActivityEventsSchema:
        pass


class FlowEventsCRUD(BaseCRUD[FlowEventsSchema]):
    async def create(self, schema: FlowEventsSchema) -> FlowEventsSchema:
        pass

    async def retrieve(self, id: int) -> FlowEventsSchema:
        pass

    async def update(self, schema: FlowEventsSchema) -> FlowEventsSchema:
        pass

    async def delete(self, id: int) -> FlowEventsSchema:
        pass
