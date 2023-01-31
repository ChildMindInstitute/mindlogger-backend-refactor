from sqlalchemy.exc import IntegrityError

from apps.answers.db.schemas import AnswerFlowItemsSchema
from apps.answers.domain import (
    AnswerFlowItem,
    AnswerFlowItemCreate,
    AnswerFlowItemsCreate,
    RespondentFlowIdentifier,
)
from apps.answers.errors import AnswerError
from infrastructure.database.crud import BaseCRUD


class AnswerFlowItemsCRUD(BaseCRUD[AnswerFlowItemsSchema]):
    schema_class = AnswerFlowItemsSchema

    async def save(
        self, schema_multiple: AnswerFlowItemsCreate
    ) -> list[AnswerFlowItem]:

        respondent_flow_identifier = RespondentFlowIdentifier(
            **schema_multiple.dict()
        )
        answer_flow_items = []

        # Save answer flow items into the database
        try:
            for answer in schema_multiple.answers:
                schema = AnswerFlowItemCreate(
                    **respondent_flow_identifier.dict(),
                    **answer.dict(),
                )

                instance: AnswerFlowItemsSchema = await self._create(
                    self.schema_class(**schema.dict())
                )

                # Create internal data model
                answer_flow_item = AnswerFlowItem.from_orm(instance)
                answer_flow_items.append(answer_flow_item)
        except IntegrityError:
            raise AnswerError

        return answer_flow_items
