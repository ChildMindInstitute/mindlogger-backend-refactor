from sqlalchemy.exc import IntegrityError

from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import (
    AnswerActivityItem,
    AnswerActivityItemCreate,
    AnswerActivityItemsCreate,
    ActivityIdentifierBase,
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
