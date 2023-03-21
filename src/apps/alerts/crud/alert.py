import uuid

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain.alert import Alert, AlertCreate
from apps.alerts.domain.alert_config import AlertConfig, AlertConfigGet
from apps.alerts.errors import (
    AlertConfigNotFoundError,
    AlertIsDeletedError,
    AlertNotFoundError,
)
from apps.shared.ordering import Ordering
from apps.shared.searching import Searching
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

    async def save(self, schema: AlertCreate) -> Alert:

        # Check if the alert config exist
        try:
            alert_config: AlertConfig = (
                await AlertConfigsCRUD().get_by_applet_item_answer(
                    AlertConfigGet(**schema.dict())
                )
            )
        except AlertConfigNotFoundError:
            raise

        # Check if the alert exist
        try:
            alert: Alert = await self.get_by_config_id_respondent_id(
                alert_config.id, schema.respondent_id
            )
        except AlertNotFoundError:
            instance: AlertSchema = await self._create(
                self.schema_class(
                    respondent_id=schema.respondent_id,
                    alert_config_id=schema.alert_config_id,
                    applet_id=schema.applet_id,
                    activity_item_histories_id_version=(
                        schema.activity_item_histories_id_version
                    ),
                )
            )
            alert = Alert.from_orm(instance)

        return alert
