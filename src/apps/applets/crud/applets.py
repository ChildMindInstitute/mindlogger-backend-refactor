from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

from apps.applets import errors
from apps.applets.db.schemas import AppletSchema, UserAppletAccessSchema
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
            raise errors.AppletNotFoundError(
                f"No such applets with {key}={value}."
            )

        return instance

    async def get_by_id(self, id_: int) -> AppletSchema:
        instance = await self._fetch(key="id", value=id_)
        return instance

    async def get_applets_by_roles(
        self, user_id_: int, roles: list[str]
    ) -> list[AppletSchema]:
        query = select(AppletSchema)
        query = query.join_from(UserAppletAccessSchema, AppletSchema)
        query = query.where(UserAppletAccessSchema.user_id == user_id_)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.order_by(AppletSchema.id)
        result: Result = await self._execute(query)
        return result.scalars().all()

    async def delete_by_id(self, id_: int):
        """Delete applets by id."""

        await self._delete(key="id", value=id_)
