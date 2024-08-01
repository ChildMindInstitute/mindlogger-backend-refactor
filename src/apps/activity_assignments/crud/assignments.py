from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityAssigmentCRUD"]


class ActivityAssigmentCRUD(BaseCRUD[ActivityAssigmentSchema]):
    schema_class = ActivityAssigmentSchema

    async def create_many(self, schemas: list[ActivityAssigmentSchema]) -> list[ActivityAssigmentSchema]:
        return await self._create_many(schemas)

    async def already_exists(self, schema: ActivityAssigmentSchema) -> bool:
        query: Query = select(ActivityAssigmentSchema)
        query = query.where(ActivityAssigmentSchema.activity_id == schema.activity_id)
        query = query.where(ActivityAssigmentSchema.respondent_id == schema.respondent_id)
        query = query.where(ActivityAssigmentSchema.invitation_id == schema.invitation_id)
        query = query.where(ActivityAssigmentSchema.target_subject_id == schema.target_subject_id)
        query = query.where(ActivityAssigmentSchema.activity_flow_id == schema.activity_flow_id)
        query = query.where(ActivityAssigmentSchema.soft_exists())
        query = query.exists()
        db_result = await self._execute(select(query))
        return db_result.scalars().first() or False
