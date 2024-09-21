import uuid

from sqlalchemy import select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.errors import IntegrationsConfigurationsTypeAlreadyAssignedToAppletError
from infrastructure.database.crud import BaseCRUD

__all__ = [
    "IntegrationsCRUD",
]


class IntegrationsCRUD(BaseCRUD[IntegrationsSchema]):
    schema_class = IntegrationsSchema

    async def create(self, schema: IntegrationsSchema) -> IntegrationsSchema:
        try:
            new_integrations = await self._create(schema)
        except IntegrityError:
            raise IntegrationsConfigurationsTypeAlreadyAssignedToAppletError(
                integration_type=schema.type, applet_id=schema.applet_id
            )
        return new_integrations

    async def retrieve_by_applet_and_type(self, applet_id: uuid.UUID, integration_type: str) -> IntegrationsSchema:
        query = select(IntegrationsSchema)
        query = query.where(IntegrationsSchema.applet_id == applet_id)
        query = query.where(IntegrationsSchema.type == integration_type)
        query = query.limit(1)
        result: Result = await self._execute(query)
        return result.scalars().first()

    async def delete_by_id(self, id: uuid.UUID):
        """Delete integrations by id."""
        await self._delete(id)
