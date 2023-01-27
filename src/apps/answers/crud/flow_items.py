from sqlalchemy.exc import IntegrityError

from apps.answers.db.schemas import AnswerFlowItemsSchema
from apps.answers.domain import AnswerFlowItem, AnswerFlowItemsCreate
from apps.answers.errors import AnswerError
from infrastructure.database.crud import BaseCRUD


class AnswerFlowItemsCRUD(BaseCRUD[AnswerFlowItemsSchema]):
    schema_class = AnswerFlowItemsSchema

    async def save(self, schema: AnswerFlowItemsCreate) -> AnswerFlowItem:
        # Save answer flow item into the database
        try:
            instance: AnswerFlowItemsSchema = await self._create(
                self.schema_class(**schema.dict())
            )
        except IntegrityError:
            raise AnswerError

        # Create internal data model
        answer_flow_item = AnswerFlowItem.from_orm(instance)

        return answer_flow_item
