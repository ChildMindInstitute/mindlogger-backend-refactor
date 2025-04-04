import uuid
from collections import defaultdict

from apps.activities.crud import ActivityItemsCRUD
from apps.activities.db.schemas import ActivityItemSchema
from apps.activities.domain.activity_create import PreparedActivityItemCreate
from apps.activities.domain.activity_full import ActivityItemFull
from apps.activities.domain.activity_item import (
    ActivityItemDuplicate,
    ActivityItemSingleLanguageDetail,
    ActivityItemSingleLanguageDetailPublic,
)
from apps.activities.domain.activity_update import PreparedActivityItemUpdate
from apps.activities.domain.response_type_config import ResponseType


class ActivityItemService:
    def __init__(self, session):
        self.session = session

    async def create(self, activity_items: list[PreparedActivityItemCreate]) -> list[ActivityItemFull]:
        schemas = list()
        activity_id_ordering_map: dict[uuid.UUID, int] = defaultdict(int)

        for activity_item in activity_items:
            schema = ActivityItemSchema(
                **activity_item.dict(),
                order=activity_id_ordering_map[activity_item.activity_id] + 1,
            )

            # Set the created_at field if it is provided by seed data
            if hasattr(activity_item, "created_at"):
                schema.created_at = getattr(activity_item, "created_at")

            schemas.append(schema)
            activity_id_ordering_map[activity_item.activity_id] += 1
        item_schemas = await ActivityItemsCRUD(self.session).create_many(schemas)
        return [ActivityItemFull.from_orm(item) for item in item_schemas]

    async def update_create(self, activity_items: list[PreparedActivityItemUpdate]):
        schemas = list()
        activity_id_ordering_map: dict[uuid.UUID, int] = defaultdict(int)

        for activity_item in activity_items:
            schemas.append(
                ActivityItemSchema(
                    **activity_item.dict(),
                    order=activity_id_ordering_map[activity_item.activity_id] + 1,
                )
            )
            activity_id_ordering_map[activity_item.activity_id] += 1
        item_schemas = await ActivityItemsCRUD(self.session).create_many(schemas)
        return [ActivityItemFull.from_orm(item) for item in item_schemas]

    async def get_single_language_by_activity_id(
        self, activity_id: uuid.UUID, language: str
    ) -> list[ActivityItemSingleLanguageDetail]:
        schemas = await ActivityItemsCRUD(self.session).get_by_activity_id(activity_id)
        items = []
        for schema in schemas:
            items.append(
                ActivityItemSingleLanguageDetail(
                    id=schema.id,
                    activity_id=schema.activity_id,
                    question=self._get_by_language(schema.question, language),
                    response_type=schema.response_type,
                    # TODO: get answers by language
                    config=schema.config,
                    response_values=schema.response_values,
                    order=schema.order,
                    name=schema.name,
                    conditional_logic=schema.conditional_logic,
                    allow_edit=schema.allow_edit,
                    is_hidden=schema.is_hidden,
                )
            )
        return items

    async def get_single_language_by_activity_ids(
        self, activity_ids: list[uuid.UUID], language: str
    ) -> dict[uuid.UUID, list[ActivityItemSingleLanguageDetailPublic]]:
        """Return all Items in map by event activity_ids."""
        schemas = await ActivityItemsCRUD(self.session).get_by_activity_ids(activity_ids)
        items_map: dict[uuid.UUID, list[ActivityItemSingleLanguageDetailPublic]] = dict()
        for schema in schemas:
            items_map.setdefault(schema.activity_id, list())
            items_map[schema.activity_id].append(
                ActivityItemSingleLanguageDetailPublic(
                    id=schema.id,
                    activity_id=schema.activity_id,
                    question=self._get_by_language(schema.question, language),
                    response_type=schema.response_type,
                    # TODO: get answers by language
                    config=schema.config,
                    response_values=schema.response_values,
                    order=schema.order,
                    name=schema.name,
                    conditional_logic=schema.conditional_logic,
                    allow_edit=schema.allow_edit,
                    is_hidden=schema.is_hidden,
                )
            )
        return items_map

    async def get_info_by_activity_ids(
        self, activity_ids: list[uuid.UUID], language: str
    ) -> dict[uuid.UUID, list[ResponseType]]:
        """Return all Items in map by event activity_ids."""
        schemas = await ActivityItemsCRUD(self.session).get_by_activity_ids(activity_ids)
        items_map: dict[uuid.UUID, list[ResponseType]] = dict()
        for schema in schemas:
            if not schema.is_hidden:
                items_map.setdefault(schema.activity_id, list())
                items_map[schema.activity_id].append(
                    schema.response_type,
                )
        return items_map

    async def get_items_by_activity_ids(self, activity_ids: list[uuid.UUID]) -> list[ActivityItemFull]:
        schemas = await ActivityItemsCRUD(self.session).get_by_activity_ids(activity_ids)
        return [ActivityItemFull.from_orm(schema) for schema in schemas]

    async def get_items_by_activity_ids_for_duplicate(
        self, activity_ids: list[uuid.UUID]
    ) -> list[ActivityItemDuplicate]:
        schemas = await ActivityItemsCRUD(self.session).get_by_activity_ids(activity_ids)
        return [ActivityItemDuplicate.from_orm(schema) for schema in schemas]

    async def remove_applet_activity_items(self, applet_id: uuid.UUID):
        await ActivityItemsCRUD(self.session).delete_by_applet_id(applet_id)

    @staticmethod
    def _get_by_language(values: dict, language: str):
        """
        Returns value by language key,
         if it does not exist,
         returns first existing or empty string
        """
        try:
            return values[language]
        except KeyError:
            for key, val in values.items():
                return val
            return ""
