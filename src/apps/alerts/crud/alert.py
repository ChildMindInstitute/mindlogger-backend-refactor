import uuid

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain.alert import Alert, AlertCreate, AlertPublic
from apps.alerts.errors import AlertIsDeletedError, AlertNotFoundError
from apps.applets.db.schemas import AppletSchema
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD


class _AlertSearching(Searching):
    search_fields = [
        AlertSchema.applet_id,
        AlertSchema.respondent_id,
        AlertSchema.activity_item_histories_id_version,
    ]


class _AlertOrdering(Ordering):
    id = AlertSchema.id
    applet_id = AlertSchema.applet_id
    respondent_id = AlertSchema.respondent_id
    created_at = AlertSchema.created_at
    updated_at = AlertSchema.updated_at


class AlertCRUD(BaseCRUD[AlertSchema]):
    schema_class = AlertSchema

    async def get_by_config_id_respondent_id(
        self, alert_config_id: uuid.UUID, respondent_id: uuid.UUID
    ) -> Alert:
        """Get alert by alert_config_id and respondent_id from the database"""

        # Get alert from the database
        query: Query = select(self.schema_class)
        query = query.where(
            self.schema_class.alert_config_id == alert_config_id
        )
        query = query.where(self.schema_class.respondent_id == respondent_id)

        result: Result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise AlertNotFoundError

        if instance.is_deleted:
            raise AlertIsDeletedError(
                message="This alert is deleted. "
                "The recovery logic is not implemented yet."
            )

        # Get internal model
        alert: Alert = Alert.from_orm(instance)

        return alert

    async def get_by_applet_id(
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[AlertPublic]:
        """Get alerts by applet_id from the database"""

        # Get alert from the database
        query: Query = (
            select(
                self.schema_class,
                AppletSchema.display_name.label("applet_name"),
                UserAppletAccessSchema.meta.label("meta"),
            )
            .where(self.schema_class.applet_id == applet_id)
            .join(
                AppletSchema.display_name,
                AppletSchema.id == self.schema_class.applet_id,
            )
            .join(
                UserAppletAccessSchema.meta,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            )
            .where(
                UserAppletAccessSchema.user_id
                == self.schema_class.respondent_id,
                UserAppletAccessSchema.applet_id
                == self.schema_class.applet_id,
            )
        )

        if query_params.search:
            query = query.where(
                *_AlertSearching().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_AlertOrdering().get_clauses(*query_params.ordering)
            )
        query = query.where(
            self.schema_class.is_deleted == False  # noqa: E712
        )
        query = paging(query, query_params.page, query_params.limit)
        result: Result = await self._execute(query)
        results = []
        for alert, applet_name, meta in result.all():
            results.append(
                AlertPublic(
                    id=alert.id,
                    is_watched=alert.is_watched,
                    alert_message=alert.alert_message,
                    respondent_id=alert.respondent_id,
                    alert_config_id=alert.alert_config_id,
                    applet_id=alert.applet_id,
                    applet_name=applet_name,
                    meta=meta,
                    created_at=alert.created_at,
                    activity_item_histories_id_version=(
                        alert.activity_item_histories_id_version
                    ),
                )
            )
        return results

    async def get_by_applet_id_count(
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
    ) -> int:
        """Get alerts count by applet_id from the database"""

        # Get alert from the database
        query: Query = select(count(self.schema_class.id))
        query = query.where(self.schema_class.applet_id == applet_id)

        if query_params.search:
            query = query.where(
                *_AlertSearching().get_clauses(query_params.search)
            )

        query = query.where(
            self.schema_class.is_deleted == False  # noqa: E712
        )

        result: Result = await self._execute(query)

        return result.scalars().first() or 0

    async def get_by_id(self, alert_id: uuid.UUID) -> AlertSchema:
        """Get alert by alert_id"""

        # Get alert from the database
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.id == alert_id)

        result: Result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise AlertNotFoundError

        if instance.is_deleted:
            raise AlertIsDeletedError(
                message="This alert is deleted. "
                "The recovery logic is not implemented yet."
            )

        return instance

    async def update(self, schema: AlertSchema) -> Alert:

        # Update alert status at is_watched true
        schema.is_watched = True
        instance: Alert = await self._update_one(
            lookup="id", value=schema.id, schema=schema
        )
        alert = Alert.from_orm(instance)

        return alert

    async def save(self, schema: AlertCreate) -> Alert:

        # Check if the alert exist
        try:
            alert: Alert = await self.get_by_config_id_respondent_id(
                schema.alert_config_id, schema.respondent_id
            )
        except AlertNotFoundError:
            instance: AlertSchema = await self._create(
                self.schema_class(
                    respondent_id=schema.respondent_id,
                    alert_config_id=schema.alert_config_id,
                    applet_id=schema.applet_id,
                    alert_message=schema.alert_message,
                    specific_answer=schema.specific_answer,
                    activity_item_histories_id_version=(
                        schema.activity_item_histories_id_version
                    ),
                )
            )
            alert = Alert.from_orm(instance)

        return alert
