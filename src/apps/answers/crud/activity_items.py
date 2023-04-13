import base64
import json
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import (
    ActivityAnswer,
    ActivityItemAnswer,
    AppletAnswerCreate,
)
from apps.applets.crud import AppletsCRUD
from apps.shared.encryption import decrypt, encrypt, generate_iv
from infrastructure.database.crud import BaseCRUD


class AnswerActivityItemsCRUD(BaseCRUD[AnswerActivityItemsSchema]):
    schema_class = AnswerActivityItemsSchema

    async def create_many(
        self, schemas: list[AnswerActivityItemsSchema]
    ) -> list[AnswerActivityItemsSchema]:
        applet = await AppletsCRUD(self.session).get_by_id(
            schemas[0].applet_id
        )
        system_encrypted_key = base64.b64decode(
            applet.system_encrypted_key.encode()
        )
        iv = generate_iv(str(applet.id))
        key = decrypt(system_encrypted_key, iv=iv)
        for schema in schemas:
            encrypted_answer = self._encrypt(
                schema.id, key, schema.answer.encode()
            )
            schema.answer = base64.b64encode(encrypted_answer).decode()

        schemas = await self._create_many(schemas)

        for schema in schemas:
            schema.answer = self._decrypt(
                schema.id, key, base64.b64decode(schema.answer.encode())
            ).decode()

        return schemas

    def _encrypt(
        self,
        unique_identifier: uuid.UUID,
        system_encrypted_key: bytes,
        value: bytes,
    ) -> bytes:
        iv = generate_iv(str(unique_identifier))
        key = decrypt(system_encrypted_key)
        encrypted_value = encrypt(value, key, iv)
        return encrypted_value

    def _decrypt(
        self,
        unique_identifier: uuid.UUID,
        system_encrypted_key: bytes,
        encrypted_value: bytes,
    ) -> bytes:
        iv = generate_iv(str(unique_identifier))
        key = decrypt(system_encrypted_key)
        answer = decrypt(encrypted_value, key, iv)
        return answer

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, user_id: uuid.UUID | None = None
    ):
        query: Query = delete(AnswerActivityItemsSchema)
        query = query.where(AnswerActivityItemsSchema.applet_id == applet_id)
        if user_id:
            query = query.where(
                AnswerActivityItemsSchema.respondent_id == user_id
            )
        await self._execute(query)

    async def get_for_answers_created(
        self,
        respondent_id: uuid.UUID,
        applet_answer: AppletAnswerCreate,
        activity_item_id_version,
    ) -> list[AnswerActivityItemsSchema]:

        answers = list()
        for activity_item_answer in applet_answer.answers:
            answers.append(json.dumps(activity_item_answer.answer.dict()))

        query: Query = select(AnswerActivityItemsSchema)
        query = query.where(
            AnswerActivityItemsSchema.applet_id == applet_answer.applet_id
        )
        query = query.where(
            AnswerActivityItemsSchema.respondent_id == respondent_id
        )
        query = query.where(
            AnswerActivityItemsSchema.activity_item_history_id
            == activity_item_id_version
        )
        query = query.where(AnswerActivityItemsSchema.answer.in_(answers))

        result = await self._execute(query)

        return result.scalars().all()

    async def get_by_answer_id(
        self, applet_id: uuid.UUID, answer_id: uuid.UUID
    ) -> ActivityAnswer:
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        system_encrypted_key = base64.b64decode(
            applet.system_encrypted_key.encode()
        )
        iv = generate_iv(str(applet.id))
        key = decrypt(system_encrypted_key, iv=iv)

        query: Query = select(
            AnswerActivityItemsSchema, ActivityItemHistorySchema
        )
        query = query.join(
            ActivityItemHistorySchema,
            ActivityItemHistorySchema.id_version
            == AnswerActivityItemsSchema.activity_item_history_id,
        )
        query = query.where(AnswerActivityItemsSchema.answer_id == answer_id)
        query = query.order_by(ActivityItemHistorySchema.order.asc())

        db_result = await self._execute(query)
        answer = ActivityAnswer()
        for (
            schema,
            item_schema,
        ) in (
            db_result.all()
        ):  # type: AnswerActivityItemsSchema, ActivityItemHistorySchema
            answer_value = self._decrypt(
                schema.id, key, base64.b64decode(schema.answer.encode())
            ).decode()
            answer.activity_item_answers.append(
                ActivityItemAnswer(
                    type=item_schema.response_type,
                    activity_item=item_schema,
                    answer=json.loads(answer_value),
                )
            )

        return answer
