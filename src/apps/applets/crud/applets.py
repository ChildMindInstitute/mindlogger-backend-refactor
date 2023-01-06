import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError

import apps.applets.db.schemas as schemas
import apps.applets.domain as domain
import apps.applets.errors as errors
from apps.activities.crud.activity import ActivitiesCRUD
from apps.activity_flows.crud.flow import FlowsCRUD
from apps.applets.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletsCRUD"]


class AppletsCRUD(BaseCRUD[schemas.AppletSchema]):
    schema_class = schemas.AppletSchema
    initial_version = "1.0.0"
    version_difference = 0.01

    def _get_version(self, previous_version: str | None = None):
        if not previous_version:
            return self.initial_version
        v1, v2, v3 = list(map(int, previous_version.split(".")))
        v3 += 1
        v2 += v3 // 10
        v1 += v2 // 10
        v3 %= 10
        v2 %= 10
        return f"{v1}.{v2}.{v3}"

    async def _fetch(self, key: str, value: Any) -> domain.applet.Applet:
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

        # Get internal model
        applet: domain.applet.Applet = domain.applet.Applet.from_orm(instance)

        return applet

    async def get_by_id(self, id_: int) -> domain.applet.Applet:
        applet = await self._fetch(key="id", value=id_)
        return applet

    async def get_full_by_id(self, id_: int) -> domain.applet.Applet:
        applet = await self._fetch(key="id", value=id_)
        applet.activities = await ActivitiesCRUD().get_by_applet_id(id_)
        applet.activity_flows = await FlowsCRUD().get_by_applet_id(id_)
        return applet

    async def get_admin_applets(
        self, user_id_: int
    ) -> list[domain.applet.Applet]:
        query = select(self.schema_class)
        query = query.join_from(
            schemas.UserAppletAccessSchema, self.schema_class
        )
        query = query.where(schemas.UserAppletAccessSchema.user_id == user_id_)
        query = query.where(schemas.UserAppletAccessSchema.role == Role.ADMIN)
        query = query.order_by(self.schema_class.id)
        result: Result = await self._execute(query)

        results: list[domain.applet.Applet] = result.scalars().all()

        return [domain.applet.Applet.from_orm(applet) for applet in results]

    async def save(
        self, user_id: int, schema: domain.applet_create.AppletCreate
    ) -> domain.applet.Applet:
        """Return applets instance and the created information."""

        try:
            instance: schemas.AppletSchema = await self._create(
                schemas.AppletSchema(
                    display_name=schema.display_name,
                    description=schema.description,
                    about=schema.about,
                    image=schema.image,
                    watermark=schema.watermark,
                    theme_id=schema.theme_id,
                    version=self._get_version(),
                    creator_id=user_id,
                    account_id=user_id,
                    report_server_ip=schema.report_server_ip,
                    report_public_key=schema.report_public_key,
                    report_recipients=schema.report_recipients,
                    report_include_user_id=schema.report_include_user_id,
                    report_include_case_id=schema.report_include_case_id,
                    report_email_body=schema.report_email_body,
                )
            )
        except IntegrityError:
            raise errors.AppletAlreadyExist()

        applet: domain.applet.Applet = domain.applet.Applet.from_orm(instance)
        activity_map: dict[uuid.UUID, int] = dict()
        applet.activities = await ActivitiesCRUD().create_many(
            applet.id, schema.activities
        )
        for activity in applet.activities:
            activity_map[activity.guid] = activity.id

        applet.activity_flows = await FlowsCRUD().create_many(
            applet.id, schema.activity_flows, activity_map
        )

        return applet

    async def delete_by_id(self, id_: int):
        """Delete applets by id."""

        await self._delete(key="id", value=id_)

    async def update_applet(
        self, user_id: int, pk: int, schema: domain.applet_update.AppletUpdate
    ) -> domain.applet.Applet:
        applet: domain.applet.Applet = await self.get_by_id(pk)
        await self._update(
            lookup="id",
            value=pk,
            payload=dict(
                display_name=schema.display_name,
                description=schema.description,
                about=schema.about,
                image=schema.image,
                watermark=schema.watermark,
                theme_id=schema.theme_id,
                version=self._get_version(applet.version),
                creator_id=user_id,
                account_id=user_id,
                report_server_ip=schema.report_server_ip,
                report_public_key=schema.report_public_key,
                report_recipients=schema.report_recipients,
                report_include_user_id=schema.report_include_user_id,
                report_include_case_id=schema.report_include_case_id,
                report_email_body=schema.report_email_body,
            ),
        )
        instance = domain.applet.Applet(
            id=pk,
            display_name=schema.display_name,
            description=schema.description,
            about=schema.about,
            image=schema.image,
            watermark=schema.watermark,
            theme_id=schema.theme_id,
            version=self._get_version(applet.version),
            report_server_ip=schema.report_server_ip,
            report_public_key=schema.report_public_key,
            report_recipients=schema.report_recipients,
            report_include_user_id=schema.report_include_user_id,
            report_include_case_id=schema.report_include_case_id,
            report_email_body=schema.report_email_body,
        )

        instance.activities = await ActivitiesCRUD().update_many(
            applet.id, schema.activities
        )

        activity_map: dict[uuid.UUID, int] = dict()
        for activity in instance.activities:
            activity_map[activity.guid] = activity.id

        instance.activity_flows = await FlowsCRUD().update_many(
            applet.id, schema.activity_flows, activity_map
        )

        return instance
