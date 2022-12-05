from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import Applet, AppletCreate, AppletUpdate
from apps.applets.errors import AppletsError, AppletsNotFoundError
from apps.authentication.db.schemas import TokenSchema
from apps.users.db import Role, UserAppletAccessSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class AppletsCRUD(BaseCRUD[TokenSchema]):
    schema_class = AppletSchema  # type: ignore[assignment]

    async def _fetch(self, key: str, value: Any) -> Applet:
        """Fetch applet by id or display_name from the database."""

        if key not in {"id", "display_name"}:
            raise AppletsError(
                f"Can not make the looking up applet by {key} {value}"
            )

        # Get applet from the database
        if not (instance := await self._get(key, value)):
            raise AppletsNotFoundError(f"No such applet with {key}={value}.")

        # Get internal model
        applet: Applet = Applet.from_orm(instance)

        return applet

    async def get_by_id(self, id_: int) -> Applet:
        return await self._fetch(key="id", value=id_)

    async def get_by_display_name(self, display_name: str) -> Applet:
        return await self._fetch(key="display_name", value=display_name)

    async def get_by_user_id_role_admin(self, user_id_: int) -> list[Applet]:
        sub_query: Query = select(UserAppletAccessSchema.applet_id).filter(
            UserAppletAccessSchema.user_id == user_id_
            and UserAppletAccessSchema.role == Role("admin")
        )
        query: Query = select(self.schema_class).where(
            self.schema_class.id in sub_query
        )

        result: Result = await self._execute(query)
        results: list[Applet] = result.scalars().all()

        return [Applet.from_orm(applet) for applet in results]

    async def save_applet(self, schema: AppletCreate) -> tuple[Applet, bool]:
        """Return applet instance and the created information."""

        # Save applet into the database
        instance: AppletSchema = await self._create(
            AppletSchema(**schema.dict())
        )

        # Create internal data model
        applet: Applet = Applet.from_orm(instance)

        return applet, True

    async def delete_by_id(self, id_: int):
        """Delete applet by id."""

        await self._delete(key="id", value=id_)

    async def delete_by_email(self, display_name: str):
        """Delete applet by display_name."""

        await self._delete(key="display_name", value=display_name)

    async def update_applet(self, id_: int, schema: AppletUpdate) -> Applet:
        await self.get_by_id(id_)
        await self._update(
            lookup=("id", id_), payload=AppletSchema(**schema.dict())
        )
        instance = await self._fetch(key="id", value=id_)

        return instance
