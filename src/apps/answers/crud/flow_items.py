import uuid

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerFlowItemsSchema
from apps.answers.domain import (
    AnswerFlowItem,
    AnswerFlowItemCreate,
    AnswerFlowItemsCreate,
    FlowIdentifierBase,
)
from apps.answers.errors import AnswerError
from infrastructure.database.crud import BaseCRUD


class AnswerFlowItemsCRUD(BaseCRUD[AnswerFlowItemsSchema]):
    schema_class = AnswerFlowItemsSchema

    async def save(
        self, schema_multiple: AnswerFlowItemsCreate
    ) -> list[AnswerFlowItem]:

        respondent_flow_identifier = FlowIdentifierBase(
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

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, user_id: uuid.UUID | None = None
    ):
        query: Query = delete(AnswerFlowItemsSchema)
        query = query.where(AnswerFlowItemsSchema.applet_id == applet_id)
        if user_id:
            query = query.where(AnswerFlowItemsSchema.respondent_id == user_id)
        await self._execute(query)
