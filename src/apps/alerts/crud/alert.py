import uuid

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Query

from apps.alerts.db.schemas import AlertSchema
from apps.applets.db.schemas import AppletHistorySchema
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.searching import Searching
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD


class _AlertSearching(Searching):
    search_fields = [
        AlertSchema.applet_id,
        AlertSchema.respondent_id,
        AlertSchema.activity_item_id,
    ]


class _AlertOrdering(Ordering):
    id = AlertSchema.id
    applet_id = AlertSchema.applet_id
    respondent_id = AlertSchema.respondent_id
    created_at = AlertSchema.created_at
    updated_at = AlertSchema.updated_at


class AlertCRUD(BaseCRUD[AlertSchema]):
    schema_class = AlertSchema

    async def create_many(
        self, schemas: list[AlertSchema]
    ) -> list[AlertSchema]:
        return await self._create_many(schemas)

    async def get_all_for_user(
        self, user_id: uuid.UUID, page: int, limit: int
    ) -> list[tuple[AlertSchema, AppletHistorySchema, UserAppletAccessSchema]]:
        query: Query = select(
            AlertSchema, AppletHistorySchema, UserAppletAccessSchema
        )
        query = query.join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.applet_id == AlertSchema.applet_id,
                UserAppletAccessSchema.user_id == AlertSchema.respondent_id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            ),
        )
        query = query.join(
            AppletHistorySchema,
            and_(
                AppletHistorySchema.id == AlertSchema.applet_id,
                AppletHistorySchema.version == AlertSchema.version,
            ),
        )
        query = query.where(AlertSchema.user_id == user_id)
        query = query.order_by(AlertSchema.created_at.desc())
        query = paging(query, page, limit)

        db_result = await self._execute(query)

        return db_result.all()

    async def get_all_for_user_count(self, user_id: uuid.UUID) -> int:
        query: Query = select(AlertSchema.id)
        query = query.where(AlertSchema.user_id == user_id)

        db_result = await self._execute(select(func.count(query.c.id)))

        return db_result.scalars().first() or 0

    async def watch(self, user_id: uuid.UUID, alert_id: uuid.UUID):
        query: Query = update(AlertSchema)
        query = query.where(AlertSchema.user_id == user_id)
        query = query.where(AlertSchema.id == alert_id)
        query = query.values(is_watched=True)

        await self._execute(query)
