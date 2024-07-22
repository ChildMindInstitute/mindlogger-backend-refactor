import uuid
from typing import Collection, List

from sqlalchemy import select
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.answers.db.schemas import AnswerNoteSchema
from apps.answers.domain import AnswerNoteDetail
from apps.answers.errors import AnswerNoteNotFoundError
from apps.shared.paging import paging
from apps.users import UserSchema
from infrastructure.database.crud import BaseCRUD


class AnswerNotesCRUD(BaseCRUD[AnswerNoteSchema]):
    schema_class = AnswerNoteSchema

    async def save(self, schema: AnswerNoteSchema) -> AnswerNoteSchema:
        return await self._create(schema)

    async def get_by_answer_id(
        self, answer_id: uuid.UUID, activity_id: uuid.UUID, page: int, limit: int
    ) -> list[AnswerNoteSchema]:
        query: Query = select(AnswerNoteSchema)
        query = query.where(AnswerNoteSchema.answer_id == answer_id)
        query = query.where(AnswerNoteSchema.activity_id == activity_id)
        query = query.order_by(AnswerNoteSchema.created_at.desc())
        query = paging(query, page, limit)

        db_result = await self._execute(query)
        return db_result.scalars().all()  # noqa

    async def get_by_submission_id(self, flow_submit_id: uuid.UUID, activity_flow_id: uuid.UUID, page: int, limit: int):
        query: Query = select(AnswerNoteSchema)
        query = query.where(AnswerNoteSchema.flow_submit_id == flow_submit_id)
        query = query.where(AnswerNoteSchema.activity_flow_id == activity_flow_id)
        query = query.order_by(AnswerNoteSchema.created_at.desc())
        query = paging(query, page, limit)
        db_result = await self._execute(query)
        return db_result.scalars().all()  # noqa

    async def get_count_by_answer_id(self, answer_id: uuid.UUID, activity_id: uuid.UUID) -> int:
        query: Query = select(count(AnswerNoteSchema.id))
        query = query.where(AnswerNoteSchema.answer_id == answer_id)
        query = query.where(AnswerNoteSchema.activity_id == activity_id)
        db_result = await self._execute(query)
        return db_result.scalars().first() or 0

    async def get_count_by_submission_id(
        self, flow_submit_id: uuid.UUID, activity_flow_id: uuid.UUID, page: int, limit: int
    ) -> int:
        query: Query = select(count(AnswerNoteSchema.id))
        query = query.where(AnswerNoteSchema.flow_submit_id == flow_submit_id)
        query = query.where(AnswerNoteSchema.activity_flow_id == activity_flow_id)
        query = paging(query, page, limit)
        db_result = await self._execute(query)
        return db_result.scalars().first() or 0

    async def get_by_id(self, note_id) -> AnswerNoteSchema:
        note = await self._get("id", note_id)
        if not note:
            raise AnswerNoteNotFoundError()
        return note

    async def update_note_by_id(self, note_id: uuid.UUID, note: str) -> AnswerNoteSchema:
        return await self._update_one("id", note_id, AnswerNoteSchema(note=note))

    async def delete_note_by_id(self, note_id: uuid.UUID):
        await self._delete(id=note_id)

    @staticmethod
    async def map_users_and_notes(
        notes: Collection[AnswerNoteSchema], users: Collection[UserSchema]
    ) -> List[AnswerNoteDetail]:
        result = []
        for note in notes:
            note_user = next(filter(lambda u: u.id == note.user_id, users))
            result.append(
                AnswerNoteDetail(
                    id=note.id,
                    user=dict(
                        id=note_user.id,
                        first_name=note_user.first_name,
                        last_name=note_user.last_name,
                    ),
                    note=note.note,
                    created_at=note.created_at,
                )
            )
        return result
