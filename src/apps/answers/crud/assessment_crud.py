import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityHistorySchema, ActivitySchema
from apps.answers.crud.answer_items import AnswerItemsCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema


class AssessmentCRUD(AnswerItemsCRUD):
    async def get_all_assessments_data(
        self,
    ) -> list[tuple[AnswerItemSchema, uuid.UUID, str]]:
        query: Query = select(AnswerItemSchema, AnswerSchema.applet_id, AnswerSchema.version)
        query = query.join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
        query = query.where(AnswerItemSchema.is_assessment.is_(True))
        result = await self._execute(query)
        return result.all()  # noqa

    async def _get_assessment_by_applet(self, applet_id: uuid.UUID) -> uuid.UUID | None:
        query: Query = select(ActivitySchema.id)
        query = query.where(
            ActivitySchema.applet_id == applet_id,
            ActivitySchema.is_reviewable.is_(True),
        )
        result = await self._execute(query)
        return result.scalars().first()

    async def _check_activity_version(self, id_version: str) -> bool:
        query: Query = select(ActivityHistorySchema)
        query = query.where(ActivityHistorySchema.id_version == id_version)
        result = await self._execute(query)
        schema: ActivityHistorySchema = result.scalars().first()
        if not schema:
            return False
        return schema.is_reviewable

    async def get_updated_assessment(
        self, answer_data: list[tuple[AnswerItemSchema, uuid.UUID, str]]
    ) -> list[AnswerSchema]:
        answers = []
        for data in answer_data:
            answer, applet_id, version = data
            activity_id = await self._get_assessment_by_applet(applet_id)
            activity_id_version = f"{activity_id}_{version}"
            is_valid = await self._check_activity_version(activity_id_version)
            if not is_valid:
                print(f"Assessment version {activity_id_version} does not exist")
                continue
            answer.assessment_activity_id = activity_id_version
            print(f"{answer.id=} {applet_id=} {activity_id_version}")
            answers.append(answer)
        return answers
