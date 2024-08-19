from sqlalchemy import select
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
                type=schema.type, applet_id=schema.applet_id
            )
        return new_integrations

    async def retrieve(self, schema: IntegrationsSchema) -> IntegrationsSchema:
        query = select(IntegrationsSchema)
        query = query.where(IntegrationsSchema.applet_id == schema.applet_id)
        query = query.where(IntegrationsSchema.type == schema.type)
        query = query.limit(1)
        result: Result = await self._execute(query)
        return result.scalars().first()
