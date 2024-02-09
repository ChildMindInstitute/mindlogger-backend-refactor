import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query
from sqlalchemy.sql import select

from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain import MlLorisUserRelationship
from apps.integrations.loris.errors import MlLorisUserRelationshipError, MlLorisUserRelationshipNotFoundError
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

        relationship: MlLorisUserRelationship = MlLorisUserRelationship.from_orm(instance)
        return relationship

    async def get_by_ml_user_id(self, ml_user_id: uuid.UUID) -> MlLorisUserRelationship:
        """Return relationship instance by ml user id."""

        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.ml_user_uuid == ml_user_id)

        result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise MlLorisUserRelationshipNotFoundError(key="ml_user_uuid", value=str(ml_user_id))

        relationship: MlLorisUserRelationship = MlLorisUserRelationship.from_orm(instance)
        return relationship


    async def get_by_loris_user_id(self, loris_user_id: str) -> MlLorisUserRelationship:
            """Return relationship instance by loris user id."""

            query: Query = select(self.schema_class)
            query = query.where(self.schema_class.loris_user_id == loris_user_id)

            result = await self._execute(query)
            instance = result.scalars().one_or_none()

            if not instance:
                raise MlLorisUserRelationshipNotFoundError(key="loris_user_id", value=str(loris_user_id))

            relationship: MlLorisUserRelationship = MlLorisUserRelationship.from_orm(instance)
            return relationship

    # async def update(self, ml_user_uuid: uuid.UUID, schema: MlLorisUserRelationshipUpdate) -> MlLorisUserRelationship:
    #     """Update relationship by ml user id."""

    #     instance = await self._update_one(
    #         lookup="ml_user_uuid",
    #         value=ml_user_uuid,
    #         schema=MlLorisUserRelationshipSchema(**schema.dict()),
    #     )
    #     relationship: MlLorisUserRelationship = MlLorisUserRelationship.from_orm(instance)
    #     return relationship
