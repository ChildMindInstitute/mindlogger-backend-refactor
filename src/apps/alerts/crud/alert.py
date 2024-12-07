import uuid

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.orm import Query

from apps.alerts.db.schemas import AlertSchema
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.integrations.db.schemas import IntegrationsSchema
from apps.shared.ordering import Ordering
from apps.shared.paging import paging
from apps.shared.searching import Searching
from apps.subjects.db.schemas import SubjectSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema, UserWorkspaceSchema
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

    async def create_many(self, schemas: list[AlertSchema]) -> list[AlertSchema]:
        return await self._create_many(schemas)

    async def get_all_for_user(
        self, user_id: uuid.UUID, page: int, limit: int
    ) -> list[
        tuple[
            AlertSchema,
            AppletHistorySchema,
            UserAppletAccessSchema,
            AppletSchema,
            UserWorkspaceSchema,
            SubjectSchema,
            IntegrationsSchema,
        ]
    ]:
        query: Query = select(
            AlertSchema,
            AppletHistorySchema,
            UserAppletAccessSchema,
            AppletSchema,
            UserWorkspaceSchema,
            SubjectSchema,
            IntegrationsSchema.type,
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
        query = query.join(
            AppletSchema,
            AppletSchema.id == AppletHistorySchema.id,
            isouter=True,
        )
        query = query.join(
            UserWorkspaceSchema,
            UserWorkspaceSchema.user_id == UserAppletAccessSchema.owner_id,
            isouter=True,
        )
        query = query.outerjoin(SubjectSchema, SubjectSchema.id == AlertSchema.subject_id)
        query = query.outerjoin(IntegrationsSchema, IntegrationsSchema.applet_id == UserAppletAccessSchema.applet_id)
        query = query.where(AlertSchema.user_id == user_id, AppletSchema.is_deleted.is_(False))
        query = query.order_by(AlertSchema.created_at.desc())
        query = paging(query, page, limit)
        db_result = await self._execute(query)
        return db_result.all()

    async def get_all_for_user_count(self, user_id: uuid.UUID) -> dict:
        query: Query = select(AlertSchema.is_watched, func.count(AlertSchema.id).label("count"))
        query = query.join(AppletSchema, AppletSchema.id == AlertSchema.applet_id)
        query = query.where(AlertSchema.user_id == user_id, AppletSchema.is_deleted.is_(False))
        query = query.group_by(AlertSchema.is_watched)
        db_result = await self._execute(query)
        db_result = db_result.all()
        result = dict(alerts_not_watched=0, alerts_all=0)
        for row in db_result:
            if row[0] is False:
                result["alerts_not_watched"] = row[1]
            result["alerts_all"] += row[1]
        return result

    async def watch(self, user_id: uuid.UUID, alert_id: uuid.UUID):
        query: Query = update(AlertSchema)
        query = query.where(AlertSchema.user_id == user_id)
        query = query.where(AlertSchema.id == alert_id)
        query = query.values(is_watched=True)

        await self._execute(query)

    async def delete_by_subject(self, subject_id: uuid.UUID):
        query = delete(AlertSchema).where(AlertSchema.subject_id == subject_id)
        await self._execute(query)
