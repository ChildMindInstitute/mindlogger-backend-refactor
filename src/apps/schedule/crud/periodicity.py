from apps.schedule.db.schemas import PeriodicitySchema
from infrastructure.database import BaseCRUD


__all__ = ["PeriodicityCRUD"]


class PeriodicityCRUD(BaseCRUD[PeriodicitySchema]):
    async def create(self, schema: PeriodicitySchema) -> PeriodicitySchema:
        pass

    async def retrieve(self, id: int) -> PeriodicitySchema:
        pass

    async def update(self, schema: PeriodicitySchema) -> PeriodicitySchema:
        pass

    async def delete(self, id: int) -> PeriodicitySchema:
        pass
