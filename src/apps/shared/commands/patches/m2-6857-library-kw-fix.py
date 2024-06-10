import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.library.crud import LibraryCRUD
from apps.library.db.schemas import LibrarySchema
from apps.library.service import LibraryService

UPDATE_KW_SQL = 'update "library" set keywords  = ARRAY[]::varchar[] where keywords is null'


async def get_libs_with_null_search_kw(session: AsyncSession, limit: int) -> list[tuple[LibrarySchema, AppletSchema]]:
    query: Query = select(LibrarySchema, AppletSchema)
    query = query.join(AppletHistorySchema, LibrarySchema.applet_id_version == AppletHistorySchema.id_version)
    query = query.join(AppletSchema, AppletSchema.id == AppletHistorySchema.id)
    query = query.where(LibrarySchema.search_keywords.is_(None))
    query = query.order_by(LibrarySchema.id.asc())
    query = query.limit(limit)
    db_result = await session.execute(query)
    result = db_result.all()
    return result


async def get_libs_with_null_search_kw_count(session: AsyncSession) -> int:
    query: Query = select(func.count(LibrarySchema.id))
    query = query.where(LibrarySchema.search_keywords.is_(None))
    db_result = await session.execute(query)
    res = db_result.first()
    return res[0]


async def set_search_kw(session: AsyncSession, library_applet: list[tuple[LibrarySchema, AppletSchema]]):
    service = LibraryService(session)
    crud = LibraryCRUD(session)
    for lib, applet in library_applet:
        kw = await service._get_search_keywords(applet, lib.applet_id_version)  # noqa
        kw.append(applet.display_name)
        lib.search_keywords = kw
        await crud.update(lib, lib.id)


async def main(
    session: AsyncSession,
    *args,
    **kwargs,
):
    try:
        # Update library.keywords
        await session.execute(UPDATE_KW_SQL)

        # Update library.search_keywords
        count = await get_libs_with_null_search_kw_count(session)
        limit = int(os.environ.get("M2_6857_BATCH_SIZE", "1000"))

        lib_applet_t = await get_libs_with_null_search_kw(session, limit)
        if count < limit:
            await set_search_kw(session, lib_applet_t)
        else:
            while len(lib_applet_t):
                await set_search_kw(session, lib_applet_t)
                lib_applet_t = await get_libs_with_null_search_kw(session, limit)

        await session.commit()
    except Exception as ex:
        await session.rollback()
        raise ex
