from sqlalchemy.exc import IntegrityError

from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import AnswerActivityItem, AnswerActivityItemsCreate
from apps.answers.errors import AnswerError
from infrastructure.database.crud import BaseCRUD


class AnswerActivityItemsCRUD(BaseCRUD[AnswerActivityItemsSchema]):
    schema_class = AnswerActivityItemsSchema

    async def save(
        self, schema: AnswerActivityItemsCreate
    ) -> AnswerActivityItem:
        # Save answer activity item into the database
        try:
            instance: AnswerActivityItemsSchema = await self._create(
                self.schema_class(**schema.dict())
            )
        except IntegrityError:
            raise AnswerError

        # Create internal data model
        answer_activity_item = AnswerActivityItem.from_orm(instance)

        return answer_activity_item
