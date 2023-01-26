from sqlalchemy.exc import IntegrityError

from apps.answers.db.schemas import AnswerSchema
from apps.answers.domain import AnswerCreate
from apps.shared.errors import NoContentError
from infrastructure.database.crud import BaseCRUD


class AnswerCRUD(BaseCRUD[AnswerSchema]):
    schema_class = AnswerSchema

    async def save(self, schema: AnswerCreate):
        # Save answer into the database
        try:
            await self._create(self.schema_class(**schema.dict()))
        except IntegrityError:
            raise Exception

        return NoContentError
