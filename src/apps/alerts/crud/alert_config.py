import uuid

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query
from sqlalchemy.sql.functions import count

from apps.alerts.db.schemas import AlertConfigSchema
from apps.alerts.domain.alert_config import (
    AlertConfig,
    AlertConfigCreate,
    AlertConfigGet,
    AlertConfigUpdate,
)
from apps.alerts.errors import (
    AlertConfigAlreadyExistError,
    AlertConfigIsDeletedError,
    AlertConfigNotFoundError,
)
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.query_params import QueryParams
from apps.shared.searching import Searching
from infrastructure.database.crud import BaseCRUD


class _AlertConfigSearching(Searching):
    search_fields = [AlertConfigSchema.activity_item_histories_id_version]


class _AlertConfigOrdering(Ordering):
    id = AlertConfigSchema.id
    applet_id = AlertConfigSchema.applet_id
    created_at = AlertConfigSchema.created_at
    updated_at = AlertConfigSchema.updated_at


class AlertConfigsCRUD(BaseCRUD[AlertConfigSchema]):
    schema_class = AlertConfigSchema

    async def get_by_applet_item_answer(
        self, schema: AlertConfigGet
    ) -> AlertConfig:
        """Get alert config by applet_id, activity item histories
        id version and specific answer from the database
        """

        # Get alert config from the database
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.applet_id == schema.applet_id)
        query = query.where(
            self.schema_class.activity_item_histories_id_version
            == schema.activity_item_histories_id_version
        )
        query = query.where(
            self.schema_class.specific_answer == schema.specific_answer
        )

        result: Result = await self._execute(query)
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

    async def get_by_applet_id(
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[AlertConfig]:
        """Get alerts config by applet_id from the database"""

        # Get alert configs from the database
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.applet_id == applet_id)

        if query_params.search:
            query = query.where(
                *_AlertConfigSearching().get_clauses(query_params.search)
            )
        if query_params.ordering:
            query = query.order_by(
                *_AlertConfigOrdering().get_clauses(*query_params.ordering)
            )
        query = query.where(
            self.schema_class.is_deleted == False  # noqa: E712
        )
        query = paging(query, query_params.page, query_params.limit)

        result: Result = await self._execute(query)
        instances: list[AlertConfigSchema] = result.scalars().all()

        return [
            AlertConfig.from_orm(alert_config) for alert_config in instances
        ]

    async def get_by_applet_id_count(
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
    ) -> int:
        """Get count alerts config by applet_id from the database"""

        # Get alert configs from the database
        query: Query = select(count(self.schema_class.id))
        query = query.where(self.schema_class.applet_id == applet_id)

        if query_params.search:
            query = query.where(
                *_AlertConfigSearching().get_clauses(query_params.search)
            )

        query = query.where(
            self.schema_class.is_deleted == False  # noqa: E712
        )

        result: Result = await self._execute(query)

        return result.scalars().first() or 0

    async def get_by_id(self, alert_config_id: uuid.UUID) -> AlertConfig:
        """Get alert config by alert_config_id from the database"""

        # Get alert config from the database
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.id == alert_config_id)

        result: Result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise AlertConfigNotFoundError

        if instance.is_deleted:
            raise AlertConfigIsDeletedError(
                message="This alert config is deleted. "
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

    async def update_by_id(
        self, pk: uuid.UUID, update_schema: AlertConfigUpdate
    ) -> AlertConfig:
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=AlertConfigSchema(**update_schema.dict()),
        )
        # Create internal data model
        alert_config = AlertConfig.from_orm(instance)
        return alert_config
