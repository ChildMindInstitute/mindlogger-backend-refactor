import uuid
from typing import Collection, List, Set, Union

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.query_params import QueryParams
from infrastructure.database.crud import BaseCRUD


class _ActivityAnswerFilter(Filtering):
    respondent_id = FilterField(AnswerSchema.respondent_id)
    from_datetime = FilterField(AnswerItemSchema.start_datetime, Comparisons.GREAT_OR_EQUAL)
    to_datetime = FilterField(AnswerItemSchema.end_datetime, Comparisons.LESS_OR_EQUAL)
    identifiers = FilterField(AnswerItemSchema.identifier, method_name="filter_by_identifiers")
    versions = FilterField(AnswerSchema.version, Comparisons.IN)

    target_subject_id = FilterField(AnswerSchema.target_subject_id)
    empty_identifiers = FilterField(AnswerItemSchema.identifier, method_name="filter_empty_identifiers")

    # TODO can be removed?
    def prepare_versions(self, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return value.split(",")
        return value

    def filter_by_identifiers(self, field, values: list | str):
        if isinstance(values, str):
            values = values.split(",")

        if isinstance(values, list):
            values = list(filter(None.__ne__, values))
            if values:
                return field.in_(values)

    def filter_empty_identifiers(self, field, value: bool):
        if not value:
            return AnswerItemSchema.identifier.isnot(None)


class AnswerItemsCRUD(BaseCRUD[AnswerItemSchema]):
    schema_class = AnswerItemSchema

    async def create(self, schema: AnswerItemSchema) -> AnswerItemSchema:
        schema = await self._create(schema)
        return schema

    async def update(self, schema: AnswerItemSchema) -> AnswerItemSchema:
        schema = await self._update_one("id", schema.id, schema)
        return schema

    async def delete_by_applet_user(self, applet_id: uuid.UUID, user_id: uuid.UUID | None = None):
        answer_id_query: Query = select(AnswerSchema.id)
        answer_id_query = answer_id_query.where(AnswerSchema.applet_id == applet_id)
        if user_id:
            answer_id_query = answer_id_query.where(AnswerSchema.respondent_id == user_id)

        query: Query = delete(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id.in_(answer_id_query))
        await self._execute(query)

    async def get_by_answer_and_activity(
        self, answer_id: uuid.UUID, activity_history_ids: List[str]
    ) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(AnswerSchema.activity_history_id.in_(activity_history_ids))
        query = query.order_by(AnswerItemSchema.created_at)

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_respondent_submits_by_answer_ids(self, answer_ids: list[uuid.UUID]) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.order_by(AnswerItemSchema.created_at.asc())
        query = query.where(AnswerItemSchema.is_assessment == False)  # noqa
        query = query.where(AnswerItemSchema.answer_id.in_(answer_ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_assessment(
        self, answer_id: uuid.UUID, user_id: uuid.UUID, submit_id: uuid.UUID | None = None
    ) -> AnswerItemSchema | None:
        """
        Return assessment for activity if not passed `submit_id`
        Otherwise returns assessment for submissions
        """
        query: Query = select(AnswerItemSchema)
        query = query.where(
            AnswerItemSchema.answer_id == answer_id,
            AnswerItemSchema.respondent_id == user_id,
            AnswerItemSchema.is_assessment.is_(True),
        )
        if submit_id:
            query = query.where(AnswerItemSchema.reviewed_flow_submit_id == submit_id)
        else:
            query = query.where(AnswerItemSchema.reviewed_flow_submit_id.is_(None))
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_answer_assessment(self, answer_item_id: uuid.UUID, answer_id: uuid.UUID) -> AnswerItemSchema | None:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.id == answer_item_id)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(AnswerItemSchema.is_assessment.is_(True))
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def assessment_hard_delete(self, answer_item_id: uuid.UUID):
        await super()._delete(id=answer_item_id, is_assessment=True)

    async def get_reviews_by_answer_id(self, answer_id: uuid.UUID) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(
            AnswerItemSchema.is_assessment.is_(True), AnswerItemSchema.reviewed_flow_submit_id.is_(None)
        )

        db_result = await self._execute(query)
        return db_result.scalars().all()  # noqa

    async def get_reviews_by_submit_id(self, submission_id: uuid.UUID) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(
            AnswerItemSchema.reviewed_flow_submit_id == submission_id, AnswerItemSchema.is_assessment.is_(True)
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()  # noqa

    async def get_respondent_answer(self, answer_id: uuid.UUID) -> AnswerItemSchema | None:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(AnswerItemSchema.is_assessment == False)  # noqa

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_applet_answers_by_activity_id(
        self,
        applet_id: uuid.UUID,
        activity_ver_ids: Collection[str],
        **filters,
    ) -> list[tuple[AnswerSchema, AnswerItemSchema]]:
        query: Query = select(AnswerSchema, AnswerItemSchema)
        query = query.join(
            AnswerItemSchema,
            and_(
                AnswerItemSchema.answer_id == AnswerSchema.id,
                AnswerItemSchema.is_assessment == False,  # noqa
            ),
            isouter=True,
        )
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.activity_history_id.in_(activity_ver_ids))
        query = query.order_by(AnswerSchema.created_at.asc())
        query = query.where(*_ActivityAnswerFilter().get_clauses(**filters))
        db_result = await self._execute(query)
        return db_result.all()  # noqa

    async def get_applet_answers_by_activity_history_ids(
        self,
        applet_id: uuid.UUID,
        activity_history_id: Union[Set[str], List[str]],
        filters: QueryParams,
    ):
        query: Query = select(AnswerSchema, AnswerItemSchema)
        query = query.join(
            AnswerItemSchema,
            and_(
                AnswerItemSchema.answer_id == AnswerSchema.id,
                AnswerItemSchema.is_assessment == False,  # noqa
            ),
            isouter=True,
        )
        query.where(
            and_(
                AnswerSchema.activity_history_id.is_(activity_history_id),
                AnswerSchema.applet_id == applet_id,
            )
        )
        query = query.order_by(AnswerSchema.created_at.asc())

        if filters.filters:
            query = query.where(*_ActivityAnswerFilter().get_clauses(**filters.filters))
        db_result = await self._execute(query)
        return db_result.all()

    async def get_assessment_activity_id(self, answer_id: uuid.UUID) -> list[tuple[uuid.UUID, str]] | None:
        query: Query = select(
            AnswerItemSchema.respondent_id,
            AnswerItemSchema.assessment_activity_id,
        )
        query = query.where(
            AnswerItemSchema.answer_id == answer_id,
            AnswerItemSchema.is_assessment.is_(True),
        )
        db_result = await self._execute(query)
        return db_result.all()  # noqa

    async def delete_assessment(self, assessment_id: uuid.UUID):
        query: Query = delete(AnswerItemSchema)
        query = query.where(AnswerItemSchema.id == assessment_id, AnswerItemSchema.is_assessment.is_(True))
        await self._execute(query)

    async def get_reviewers_by_answers(self, answer_ids: list[uuid.UUID]) -> list[tuple[uuid.UUID, list[uuid.UUID]]]:
        query: Query = select(AnswerItemSchema.answer_id, func.array_agg(AnswerItemSchema.respondent_id))
        query = query.where(
            AnswerItemSchema.answer_id.in_(answer_ids),
            AnswerItemSchema.is_assessment.is_(True),
            AnswerItemSchema.reviewed_flow_submit_id.is_(None),
        )
        query = query.group_by(AnswerItemSchema.answer_id)
        db_result = await self._execute(query)
        return db_result.all()  # noqa

    async def get_reviewers_by_submission(
        self, submission_ids: list[uuid.UUID]
    ) -> list[tuple[uuid.UUID, list[uuid.UUID]]]:
        query: Query = select(AnswerItemSchema.reviewed_flow_submit_id, func.array_agg(AnswerItemSchema.respondent_id))
        query = query.where(
            AnswerItemSchema.is_assessment.is_(True), AnswerItemSchema.reviewed_flow_submit_id.in_(submission_ids)
        )
        query = query.group_by(AnswerItemSchema.reviewed_flow_submit_id)
        db_result = await self._execute(query)
        return db_result.all()  # noqa
