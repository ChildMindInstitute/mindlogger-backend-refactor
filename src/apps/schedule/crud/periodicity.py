import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Query

from apps.schedule.db.schemas import PeriodicitySchema
from apps.schedule.domain.schedule.internal import Periodicity
from apps.schedule.domain.schedule.requests import PeriodicityRequest
from apps.schedule.errors import PeriodicityNotFoundError
from infrastructure.database import BaseCRUD

__all__ = ["PeriodicityCRUD"]


class PeriodicityCRUD(BaseCRUD[PeriodicitySchema]):
    schema_class = PeriodicitySchema

    async def save(self, schema: PeriodicityRequest) -> Periodicity:
        """Return periodicity instance and the created information."""
        instance: PeriodicitySchema = await self._create(PeriodicitySchema(**schema.dict()))
        periodicity: Periodicity = Periodicity.from_orm(instance)
        return periodicity

    async def get_by_id(self, pk: uuid.UUID) -> Periodicity:
        """Return periodicity instance."""

        if not (instance := await self._get("id", pk)):
            raise PeriodicityNotFoundError(key="id", value=str(id))

        periodicity: Periodicity = Periodicity.from_orm(instance)
        return periodicity

    async def delete_by_ids(self, periodicity_ids: list[uuid.UUID]) -> None:
        """Delete all periodicities by if id in list."""
        query: Query = delete(PeriodicitySchema)
        query = query.where(PeriodicitySchema.id.in_(periodicity_ids))
        await self._execute(query)

    async def update(self, pk: uuid.UUID, schema: PeriodicityRequest) -> Periodicity:
        """Update periodicity instance."""
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=PeriodicitySchema(**schema.dict()),
        )
        periodicity: Periodicity = Periodicity.from_orm(instance)
        return periodicity
