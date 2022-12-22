from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.items.db.schemas import ItemTemplateSchema
from apps.items.domain.item_templates import (
    ItemTemplate,
    ItemTemplateCreate,
    PublicItemTemplate,
)
from apps.items.errors import ItemTemplateAlreadyExist
from infrastructure.database.crud import BaseCRUD

__all__ = ["ItemTemplatesCRUD"]


class ItemTemplatesCRUD(BaseCRUD[ItemTemplateSchema]):
    schema_class = ItemTemplateSchema

    async def get_item_templates(
        self, user_id_: int
    ) -> list[PublicItemTemplate]:
        query: Query = (
            select(self.schema_class)
            .where(self.schema_class.user_id == user_id_)
            .order_by(self.schema_class.id)
        )

        result: Result = await self._execute(query)
        results: list[PublicItemTemplate] = result.scalars().all()

        return [
            PublicItemTemplate.from_orm(item_template)
            for item_template in results
        ]

    async def save(self, schema: ItemTemplateCreate) -> ItemTemplate:
        """Return item template instance and the created information."""

        # Save item template into the database
        try:
            instance: ItemTemplateSchema = await self._create(
                ItemTemplateSchema(**schema.dict())
            )
        except IntegrityError:
            raise ItemTemplateAlreadyExist()

        # Create internal data model
        item_template: ItemTemplate = ItemTemplate.from_orm(instance)

        return item_template

    async def delete_by_id(self, id_: int):
        """Delete item template by id."""

        await self._delete(key="id", value=id_)
