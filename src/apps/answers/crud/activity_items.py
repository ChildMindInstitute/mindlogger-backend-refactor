import uuid

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import (
    ActivityIdentifierBase,
    AnswerActivityItem,
    AnswerActivityItemCreate,
    AnswerActivityItemsCreate,
)
from apps.answers.errors import AnswerError
from infrastructure.database.crud import BaseCRUD


class AnswerActivityItemsCRUD(BaseCRUD[AnswerActivityItemsSchema]):
    schema_class = AnswerActivityItemsSchema

    async def save(
        self, schema_multiple: AnswerActivityItemsCreate
    ) -> list[AnswerActivityItem]:

        respondent_activity_identifier = ActivityIdentifierBase(
            **schema_multiple.dict()
        )
        answer_activity_items = []

        # Save answer activity items into the database
        try:
            for answer in schema_multiple.answers:
                schema = AnswerActivityItemCreate(
                    **respondent_activity_identifier.dict(),
                    **answer.dict(),
                )

                instance: AnswerActivityItemsSchema = await self._create(
                    self.schema_class(**schema.dict())
                )
                # Create internal data model
                answer_activity_item = AnswerActivityItem.from_orm(instance)
                answer_activity_items.append(answer_activity_item)

        except IntegrityError:
            raise AnswerError

        return answer_activity_items

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
