from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.alerts.db.schemas import AlertConfigSchema
from apps.alerts.domain.alert_config import (
    AlertConfig,
    AlertConfigCreate,
    AlertConfigGet,
)
from apps.alerts.errors import (
    AlertConfigAlreadyExistError,
    AlertConfigIsDeletedError,
    AlertConfigNotFoundError,
)
from infrastructure.database.crud import BaseCRUD


class AlertConfigsCRUD(BaseCRUD[AlertConfigSchema]):
    schema_class = AlertConfigSchema

    async def get_by_applet_item_answer(
        self, schema: AlertConfigGet
    ) -> AlertConfig:
        """Get alert config by applet_id, activity_item_id and
        specific answer from the database
        """

        # Get alert config from the database
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.applet_id == schema.applet_id)
        query = query.where(
            self.schema_class.activity_item_id == schema.activity_item_id
        )
        query = query.where(
            self.schema_class.specific_answer == schema.specific_answer
        )

        result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise AlertConfigNotFoundError

        if instance.is_deleted:
            raise AlertConfigIsDeletedError(
                "This alert config is deleted. "
                "The recovery logic is not implemented yet."
            )

        # Get internal model
        alert_config: AlertConfig = AlertConfig.from_orm(instance)

        return alert_config

    async def save(self, schema: AlertConfigCreate) -> AlertConfig:

        # Save alert config into the database
        try:
            await self.get_by_applet_item_answer(
                AlertConfigGet(**schema.dict())
            )
        except AlertConfigNotFoundError:
            instance: AlertConfigSchema = await self._create(
                self.schema_class(**schema.dict())
            )
            alert_config: AlertConfig = AlertConfig.from_orm(instance)
        else:
            raise AlertConfigAlreadyExistError

        return alert_config
