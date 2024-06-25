import uuid

from sqlalchemy import Unicode, or_, select
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletHistorySchema
from apps.library.db.schemas import CartSchema, LibrarySchema
from apps.library.domain import LibraryItem
from apps.library.errors import LibraryItemDoesNotExistError
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from infrastructure.database.crud import BaseCRUD


class LibraryCRUD(BaseCRUD[LibrarySchema]):
    schema_class = LibrarySchema

    async def save(self, schema: LibrarySchema):
        return await self._create(schema)

    async def update(self, schema: LibrarySchema, library_id: uuid.UUID):
        schema = await self._update_one("id", library_id, schema)
        return schema

    async def get_by_id(self, id: uuid.UUID) -> LibrarySchema | None:
        schema = await self._get("id", id)
        return schema

    async def get_by_applet_id_version(self, applet_id_version: str) -> LibrarySchema | None:
        schema = await self._get("applet_id_version", applet_id_version)
        return schema

    async def get_all_library_count(self, query_params: QueryParams) -> int:
        query: Query = select(LibrarySchema.id)
        if query_params.search:
            query = query.where(
                or_(
                    LibrarySchema.search_keywords.cast(Unicode()).ilike(f"%{query_params.search}%"),
                    LibrarySchema.keywords.cast(Unicode()).ilike(f"%{query_params.search}%"),
                )
            )
        results = await self._execute(query)
        return len(results.all())

    async def get_all_library_items(
        self,
        query_params: QueryParams,
    ) -> list[LibrarySchema]:
        query: Query = select(
            LibrarySchema.id,
            LibrarySchema.keywords,
            LibrarySchema.applet_id_version,
            AppletHistorySchema.display_name,
            AppletHistorySchema.description,
            AppletHistorySchema.about,
            AppletHistorySchema.image,
            AppletHistorySchema.watermark,
        )
        query = query.join(
            AppletHistorySchema,
            LibrarySchema.applet_id_version == AppletHistorySchema.id_version,
        )
        if query_params.search:
            query = query.where(
                or_(
                    LibrarySchema.search_keywords.cast(Unicode()).ilike(f"%{query_params.search}%"),
                    LibrarySchema.keywords.cast(Unicode()).ilike(f"%{query_params.search}%"),
                )
            )
        query = paging(query, query_params.page, query_params.limit)

        results = await self._execute(query)
        return results.all()  # noqa

    async def get_library_item_by_id(self, id_: uuid.UUID) -> LibraryItem:
        query: Query = select(
            LibrarySchema.id,
            LibrarySchema.keywords,
            LibrarySchema.applet_id_version,
            AppletHistorySchema.display_name,
            AppletHistorySchema.description,
            AppletHistorySchema.about,
            AppletHistorySchema.image,
            AppletHistorySchema.watermark,
        )
        query = query.join(
            AppletHistorySchema,
            LibrarySchema.applet_id_version == AppletHistorySchema.id_version,
        )
        query = query.where(LibrarySchema.id == id_)
        result = await self._execute(query)
        db_result = result.first()
        if not db_result:
            raise LibraryItemDoesNotExistError()

        return LibraryItem.from_orm(db_result)

    async def check_applet_name(self, name: str):
        query: Query = select(AppletHistorySchema.display_name)
        query = query.join(
            LibrarySchema,
            LibrarySchema.applet_id_version == AppletHistorySchema.id_version,
        )
        query = query.where(AppletHistorySchema.display_name == name)
        query = query.exists()

        result = await self._execute(select(query))

        return result.scalars().first()


class CartCRUD(BaseCRUD[CartSchema]):
    schema_class = CartSchema

    async def save(self, schema: CartSchema):
        return await self._create(schema)

    async def get_by_user_id(self, user_id: uuid.UUID) -> CartSchema | None:
        schema = await self._get("user_id", user_id)
        return schema
