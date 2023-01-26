from apps.schedule.db.schemas import PeriodicitySchema
from apps.schedule.domain.schedule.internal import Periodicity
from apps.schedule.domain.schedule.requests import PeriodicityRequest
from apps.schedule.errors import PeriodicityNotFoundError
from infrastructure.database import BaseCRUD

__all__ = ["PeriodicityCRUD"]


class PeriodicityCRUD(BaseCRUD[PeriodicitySchema]):
    async def save(self, schema: PeriodicityRequest) -> Periodicity:
        """Return periodicity instance and the created information."""
        instance: PeriodicitySchema = await self._create(
            PeriodicitySchema(**schema.dict())
        )
        periodicity: Periodicity = Periodicity.from_orm(instance)
        return periodicity

    async def get_by_id(self, id: int) -> Periodicity:
        """Return periodicity instance."""

        if not (instance := await self._get("id", id)):
            raise PeriodicityNotFoundError(key="id", value=str(id))

        periodicity: Periodicity = Periodicity.from_orm(instance)
        return periodicity

    # async def update(self, schema: PeriodicitySchema) -> PeriodicitySchema:
    #     pass

    # async def delete(self, id: int) -> PeriodicitySchema:
    #     pass
