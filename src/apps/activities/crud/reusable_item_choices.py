import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.activities.db.schemas import ReusableItemChoiceSchema
from apps.activities.domain.reusable_item_choices import (
    PublicReusableItemChoice,
    ReusableItemChoice,
    ReusableItemChoiceCreate,
)
from apps.activities.errors import (
    ReusableItemChoiceAlreadyExist,
    ReusableItemChoiceDoeNotExist,
)
from infrastructure.database.crud import BaseCRUD

__all__ = ["ReusableItemChoiceCRUD"]


class ReusableItemChoiceCRUD(BaseCRUD[ReusableItemChoiceSchema]):
    schema_class = ReusableItemChoiceSchema

    async def get_item_templates(
        self, user_id_: uuid.UUID
    ) -> list[PublicReusableItemChoice]:
        query: Query = select(ReusableItemChoiceSchema)
        query = query.where(ReusableItemChoiceSchema.user_id == user_id_)
        query = query.order_by(ReusableItemChoiceSchema.id)
        db_result = await self._execute(query)

        return [
            PublicReusableItemChoice.from_orm(item_template)
            for item_template in db_result.scalars().all()
        ]

    async def get_item_templates_count(self, user_id_: uuid.UUID) -> int:
        query: Query = select(count(ReusableItemChoiceSchema.id))
        query = query.where(ReusableItemChoiceSchema.user_id == user_id_)
        db_result = await self._execute(query)

        return db_result.scalars().first() or 0

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
        schema = await self._get("id", id_)
        if not schema:
            raise ReusableItemChoiceDoeNotExist()

        await self._delete(key="id", value=id_)
