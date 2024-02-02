import uuid
from typing import Collection, List, Set, Union

from sqlalchemy import and_, delete, select
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

    def prepare_identifiers(self, value: str):
        if value == "":
            return None
        return value.split(",")

    def prepare_versions(self, value: str):
        return value.split(",")

    def filter_by_identifiers(self, field, values: list | None):
        if values is None:
            return field == None  # noqa
        return field.in_(values)


class AnswerItemsCRUD(BaseCRUD[AnswerItemSchema]):
    schema_class = AnswerItemSchema

    async def create(self, schema: AnswerItemSchema):
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

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_answer_ids(self, answer_ids: list[uuid.UUID]) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id.in_(answer_ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_respondent_submits_by_answer_ids(self, answer_ids: list[uuid.UUID]) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.order_by(AnswerItemSchema.created_at.asc())
        query = query.where(AnswerItemSchema.is_assessment == False)  # noqa
        query = query.where(AnswerItemSchema.answer_id.in_(answer_ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_assessment(self, answer_id: uuid.UUID, user_id: uuid.UUID) -> AnswerItemSchema | None:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(AnswerItemSchema.respondent_id == user_id)
        query = query.where(AnswerItemSchema.is_assessment == True)  # noqa
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_reviews_by_answer_id(self, answer_id: uuid.UUID, activity_items: list) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(AnswerItemSchema.is_assessment.is_(True))

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
        filters: QueryParams,
    ) -> list[tuple[AnswerSchema, AnswerItemSchema]]:
        identifiers = filters.filters.get("identifiers")
        empty_identifiers = filters.filters.get("empty_identifiers")

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
        if not identifiers and empty_identifiers:
            if "identifiers" in filters.filters:
                filters.filters.pop("identifiers")
        elif not identifiers and not empty_identifiers:
            filters.filters.pop("identifiers")
            query = query.where(AnswerItemSchema.identifier.isnot(None))

        query = query.order_by(AnswerSchema.created_at.asc())
        if filters.filters:
            query = query.where(*_ActivityAnswerFilter().get_clauses(**filters.filters))
        db_result = await self._execute(query)
        return db_result.all()

    async def get_applet_answers_by_activity_history_ids(
        self,
        applet_id: uuid.UUID,
        activity_history_id: Union[Set[str], List[str]],
        filters: QueryParams,
    ):
        identifiers = filters.filters.get("identifiers")
        empty_identifiers = filters.filters.get("empty_identifiers")
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

        if not identifiers:
            if "identifiers" in filters.filters:
                filters.filters.pop("identifiers")
            if empty_identifiers:
                query = query.where(AnswerItemSchema.identifier.is_(None))

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
