import uuid

from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query
from sqlalchemy.sql import select

from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain.domain import MlLorisUserRelationship
from apps.integrations.loris.errors import MlLorisUserRelationshipError
from infrastructure.database import BaseCRUD

__all__ = [
    "MlLorisUserRelationshipCRUD",
]


class MlLorisUserRelationshipCRUD(BaseCRUD[MlLorisUserRelationshipSchema]):
    schema_class = MlLorisUserRelationshipSchema

    async def save(self, schema: MlLorisUserRelationshipSchema) -> MlLorisUserRelationship:
        """Return relationship instance and the created information."""

        try:
            instance: MlLorisUserRelationshipSchema = await self._create(schema)
        except IntegrityError as e:
            raise MlLorisUserRelationshipError(message=str(e))

        relationship: MlLorisUserRelationship = MlLorisUserRelationship.model_validate(instance)
        return relationship

    async def get_by_ml_user_ids(self, ml_user_ids: list[uuid.UUID]) -> list[MlLorisUserRelationship]:
        """Return relationship instance by ml user id."""

        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.ml_user_uuid.in_(ml_user_ids))

        result = await self._execute(query)
        instances = result.scalars().all()

        return TypeAdapter(list[MlLorisUserRelationship]).validate_python(instances)

    async def get_by_loris_user_ids(self, loris_user_ids: list[str]) -> list[MlLorisUserRelationship]:
        """Return relationship instance by loris user id."""

        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.loris_user_id.in_(loris_user_ids))

        result = await self._execute(query)
        instances = result.scalars().all()

        return TypeAdapter(list[MlLorisUserRelationship]).validate_python(instances)

    # async def update(self, ml_user_uuid: uuid.UUID, schema: MlLorisUserRelationshipUpdate) -> MlLorisUserRelationship:
    #     """Update relationship by ml user id."""

    #     instance = await self._update_one(
    #         lookup="ml_user_uuid",
    #         value=ml_user_uuid,
    #         schema=MlLorisUserRelationshipSchema(**schema.model_dump()),
    #     )
    #     relationship: MlLorisUserRelationship = MlLorisUserRelationship.model_validate(instance)
    #     return relationship
