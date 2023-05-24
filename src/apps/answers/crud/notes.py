import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.answers.db.schemas import AnswerNoteSchema
from apps.answers.domain import AnswerNoteDetail
from apps.answers.errors import AnswerNoteNotFoundError
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.users import UserSchema
from infrastructure.database.crud import BaseCRUD


class AnswerNotesCRUD(BaseCRUD[AnswerNoteSchema]):
    schema_class = AnswerNoteSchema

    async def save(self, schema: AnswerNoteSchema):
        return await self._create(schema)

    async def get_by_answer_id(
        self,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[AnswerNoteDetail]:
        query: Query = select(AnswerNoteSchema, UserSchema)
        query = query.join(
            UserSchema, UserSchema.id == AnswerNoteSchema.user_id
        )
        query = query.where(AnswerNoteSchema.answer_id == answer_id)
        query = query.where(AnswerNoteSchema.activity_id == activity_id)
        query = query.order_by(AnswerNoteSchema.created_at.desc())
        query = paging(query, query_params.page, query_params.limit)

        db_result = await self._execute(query)
        results = []
        for (
            schema,
            user_schema,
        ) in db_result.all():  # type: AnswerNoteSchema, UserSchema
            results.append(
                AnswerNoteDetail(
                    id=schema.id,
                    user=dict(
                        first_name=user_schema.first_name,
                        last_name=user_schema.last_name,
                    ),
                    note=schema.note,
                    created_at=schema.created_at,
                )
            )
        return results

    async def get_count_by_answer_id(
        self, answer_id: uuid.UUID, activity_id: uuid.UUID
    ) -> int:
        query: Query = select(count(AnswerNoteSchema.id))
        query = query.where(AnswerNoteSchema.answer_id == answer_id)
        query = query.where(AnswerNoteSchema.activity_id == activity_id)
        db_result = await self._execute(query)
        return db_result.scalars().first() or 0

    async def get_by_id(self, note_id) -> AnswerNoteSchema:
        note = await self._get("id", note_id)
        if not note:
            raise AnswerNoteNotFoundError()
        return note

    async def update_note_by_id(
        self, note_id: uuid.UUID, note: str
    ) -> AnswerNoteSchema:
        return await self._update_one(
            "id", note_id, AnswerNoteSchema(note=note)
        )

    async def delete_note_by_id(self, note_id: uuid.UUID):
        await self._delete("id", note_id)
