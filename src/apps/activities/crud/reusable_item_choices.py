import uuid

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ReusableItemChoiceSchema
from apps.activities.domain.reusable_item_choices import (
    PublicReusableItemChoice,
    ReusableItemChoice,
    ReusableItemChoiceCreate,
)
from apps.activities.errors import ReusableItemChoiceAlreadyExist
from infrastructure.database.crud import BaseCRUD

__all__ = ["ReusableItemChoiceCRUD"]


class ReusableItemChoiceCRUD(BaseCRUD[ReusableItemChoiceSchema]):
    schema_class = ReusableItemChoiceSchema

    async def get_item_templates(
        self, user_id_: uuid.UUID
    ) -> list[PublicReusableItemChoice]:
        query: Query = (
            select(self.schema_class)
            .where(self.schema_class.user_id == user_id_)
            .order_by(self.schema_class.id)
        )

        result: Result = await self._execute(query)
        results: list[PublicReusableItemChoice] = result.scalars().all()

        return [
            PublicReusableItemChoice.from_orm(item_template)
            for item_template in results
        ]

    async def save(
        self, schema: ReusableItemChoiceCreate
    ) -> ReusableItemChoice:
        """Return item template instance and the created information."""

        # Save item template into the database
        try:
            instance: ReusableItemChoiceSchema = await self._create(
                ReusableItemChoiceSchema(**schema.dict())
            )
        except IntegrityError:
            raise ReusableItemChoiceAlreadyExist()

        # Create internal data model
        item_template: ReusableItemChoice = ReusableItemChoice.from_orm(
            instance
        )

        return item_template

    async def delete_by_id(self, id_: uuid.UUID):
        """Delete item template by id."""

        await self._delete(key="id", value=id_)
