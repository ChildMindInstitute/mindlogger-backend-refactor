from typing import Any

from sqlalchemy import distinct, or_, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from apps.applets import errors
from apps.applets.db.schemas import AppletSchema, UserAppletAccessSchema
from apps.applets.domain import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class AppletsCRUD(BaseCRUD[AppletSchema]):
    schema_class = AppletSchema

    async def save(self, schema: AppletSchema) -> AppletSchema:
        """Return applets instance and the created information."""

        try:
            instance: AppletSchema = await self._create(schema)
        except IntegrityError:
            raise errors.AppletAlreadyExist()
        return instance

    async def update_by_id(
        self, pk: int, schema: AppletSchema
    ) -> AppletSchema:
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=schema,
        )
        return instance

    async def _fetch(self, key: str, value: Any) -> AppletSchema:
        """Fetch applets by id or display_name from the database."""

        if key not in {"id", "display_name"}:
            raise errors.AppletsError(
                f"Can not make the looking up applets by {key} {value}"
            )

        # Get applets from the database
        if not (instance := await self._get(key, value)):
            raise errors.AppletNotFoundError(key=key, value=value)

        return instance

    async def get_by_id(self, id_: int) -> AppletSchema:
        instance = await self._fetch(key="id", value=id_)
        return instance

    async def exist_by_id(self, id_: int) -> bool:
        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.id == id_)

        db_result = await self._execute(query)

        return db_result.scalars().one_or_none() is not None

    async def get_applets_by_roles(
        self, user_id: int, roles: list[str]
    ) -> list[AppletSchema]:
        accessible_applets_query = select(UserAppletAccessSchema.applet_id)
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.user_id == user_id
        )
        accessible_applets_query = accessible_applets_query.where(
            UserAppletAccessSchema.role.in_(roles)
        )

        query = select(AppletSchema)
        query = query.where(AppletSchema.id.in_(accessible_applets_query))
        query = query.order_by(AppletSchema.id)
        result: Result = await self._execute(query)
        return result.scalars().all()

    async def get_applet_by_role(
        self, user_id: int, applet_id: int, roles: list[str]
    ) -> AppletSchema:
        query = select(AppletSchema)
        query = query.join_from(UserAppletAccessSchema, AppletSchema)
        query = query.where(AppletSchema.id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.limit(1)
        result: Result = await self._execute(query)
        try:
            return result.scalars().one()
        except Exception as e:
            raise e

    async def delete_by_id(self, id_: int):
        """Delete applets by id."""

        query = update(AppletSchema)
        query = query.where(AppletSchema.id == id_)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def check_folder(self, folder_id: int) -> bool:
        """
        Checks whether folder has applets
        """
        query: Query = select(AppletSchema.id)
        query = query.where(AppletSchema.folder_id == folder_id)
        query = query.limit(1)
        query = query.exists()
        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def set_applets_folder(
        self, applet_id: int, folder_id: int | None
    ) -> AppletSchema:
        query = update(AppletSchema)
        query = query.values(folder_id=folder_id)
        query = query.where(AppletSchema.id == applet_id)
        query = query.returning(self.schema_class)
        db_result = await self._execute(query)

        return db_result.scalars().one_or_none()

    async def get_folder_applets(
        self, owner_id: int, folder_id: int
    ) -> list[AppletSchema]:
        access_query: Query = select(
            distinct(UserAppletAccessSchema.applet_id)
        )
        access_query = access_query.where(
            UserAppletAccessSchema.user_id == owner_id
        )
        access_query = access_query.where(
            UserAppletAccessSchema.role.in_([Role.ADMIN])
        )

        query: Query = select(AppletSchema)
        query = query.where(AppletSchema.folder_id == folder_id)
        query = query.where(AppletSchema.id.in_(access_query))

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_name_duplicates(
        self, user_id: int, name: str, exclude_applet_id: int | None = None
    ) -> list[str]:
        query: Query = select(distinct(AppletSchema.display_name))
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.applet_id == AppletSchema.id,
        )
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        if exclude_applet_id:
            query = query.where(AppletSchema.id != exclude_applet_id)
        query = query.where(
            or_(
                AppletSchema.display_name.op("~")(f"{name} \\(\\d+\\)"),
                AppletSchema.display_name == name,
            )
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()
