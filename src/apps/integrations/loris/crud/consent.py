import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query
from sqlalchemy.sql import select

from apps.integrations.loris.db.schemas import ConsentSchema
from apps.integrations.loris.domain.domain import Consent, ConsentCreate, ConsentUpdate
from apps.integrations.loris.errors import ConsentError, ConsentNotFoundError
from infrastructure.database import BaseCRUD

__all__ = [
    "ConsentCRUD",
]


class ConsentCRUD(BaseCRUD[ConsentSchema]):
    schema_class = ConsentSchema

    async def save(self, schema: ConsentCreate) -> Consent:
        """Return consent instance and the created information."""

        try:
            instance: ConsentSchema = await self._create(ConsentSchema(**schema.dict()))
        # Raise exception if applet doesn't exist
        except IntegrityError as e:
            raise ConsentError(message=str(e))

        event: Consent = Consent.from_orm(instance)
        return event

    async def get_by_id(self, pk: uuid.UUID) -> Consent:
        """Return consent instance."""

        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.id == pk)

        result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise ConsentNotFoundError(key="id", value=str(pk))

        event: Consent = Consent.from_orm(instance)
        return event

    async def get_by_user_id(self, user_id: uuid.UUID) -> Consent:
        """Return consent instance by user id."""

        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.user_id == user_id)

        result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise ConsentNotFoundError(key="user_id", value=str(user_id))

        event: Consent = Consent.from_orm(instance)
        return event

    async def update(self, pk: uuid.UUID, schema: ConsentUpdate) -> Consent:
        """Update consent by consent id."""

        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=ConsentSchema(**schema.dict()),
        )
        event: Consent = Consent.from_orm(instance)
        return event
