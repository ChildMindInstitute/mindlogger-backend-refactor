import datetime
import uuid

from pydantic import parse_obj_as
from sqlalchemy import (
    and_,
    any_,
    case,
    delete,
    exists,
    func,
    literal_column,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Query

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activities.domain import ActivityHistory
from apps.activities.domain.activity_item_history import ActivityItemHistory
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.alerts.errors import AnswerNotFoundError
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import UserAnswerData
from apps.shared.filtering import FilterField, Filtering
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD


class _AnswersExportFilter(Filtering):
    respondent_id = FilterField(AnswerSchema.respondent_id)


class AnswersCRUD(BaseCRUD[AnswerSchema]):
    schema_class = AnswerSchema

    async def create(self, schema: AnswerSchema):
        schema = await self._create(schema)
        return schema

    async def create_many(
        self, schemas: list[AnswerSchema]
    ) -> list[AnswerSchema]:
        schemas = await self._create_many(schemas)
        return schemas

    async def get_respondents_answered_activities_by_applet_id(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[AnswerSchema]:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.respondent_id == respondent_id)
        query = query.where(func.date(AnswerSchema.created_at) == created_date)
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_respondents_submit_dates(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[datetime.date]:
        query: Query = select(func.date(AnswerSchema.created_at))
        query = query.where(AnswerSchema.respondent_id == respondent_id)
        query = query.where(func.date(AnswerSchema.created_at) >= from_date)
        query = query.where(func.date(AnswerSchema.created_at) <= to_date)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_id(self, id_: uuid.UUID) -> AnswerSchema:
        schema = await self._get("id", id_)
        if not schema:
            raise AnswerNotFoundError()
        return schema

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None = None
    ):
        query: Query = delete(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        if respondent_id:
            query = query.where(AnswerSchema.respondent_id == respondent_id)
        await self._execute(query)

    async def get_applet_answers(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, **filters
    ) -> list[UserAnswerData]:
        assigned_respondents = select(
            literal_column("val").cast(UUID)
        ).select_from(
            func.jsonb_array_elements_text(
                case(
                    (
                        func.jsonb_typeof(
                            UserAppletAccessSchema.meta[text("'respondents'")]
                        )
                        == text("'array'"),
                        UserAppletAccessSchema.meta[text("'respondents'")],
                    ),
                    else_=text("'[]'::jsonb"),
                )
            ).alias("val")
        )

        has_access = (
            exists()
            .where(
                UserAppletAccessSchema.user_id == user_id,
                UserAppletAccessSchema.applet_id == AnswerSchema.applet_id,
                or_(
                    UserAppletAccessSchema.role.in_(
                        [Role.OWNER, Role.MANAGER]
                    ),
                    and_(
                        UserAppletAccessSchema.role == Role.REVIEWER,
                        AnswerSchema.respondent_id
                        == any_(assigned_respondents.scalar_subquery()),
                    ),
                ),
            )
            .correlate(AnswerSchema)
        )

        is_manager = (
            exists()
            .where(
                UserAppletAccessSchema.user_id == UserSchema.id,
                UserAppletAccessSchema.applet_id == AnswerSchema.applet_id,
                UserAppletAccessSchema.role != Role.RESPONDENT,
            )
            .correlate(AnswerSchema, UserSchema)
        )

        query: Query = (
            select(
                AnswerSchema.id,
                AnswerSchema.version,
                AnswerSchema.user_public_key,
                AnswerSchema.respondent_id,
                UserAppletAccessSchema.respondent_nickname,
                UserAppletAccessSchema.respondent_secret_id,
                UserSchema.email.label("respondent_email"),
                is_manager.label("is_manager"),
                AnswerItemSchema.answer,
                AnswerItemSchema.item_ids,
                AnswerItemSchema.applet_history_id,
                AnswerItemSchema.activity_history_id,
                AnswerItemSchema.flow_history_id,
                ActivityFlowHistoriesSchema.name.label("flow_name"),
                AnswerItemSchema.created_at,
            )
            .select_from(AnswerSchema)
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
            .outerjoin(
                ActivityFlowHistoriesSchema,
                ActivityFlowHistoriesSchema.id_version
                == AnswerItemSchema.flow_history_id,
            )
            .outerjoin(UserSchema, UserSchema.id == AnswerSchema.respondent_id)
            .outerjoin(
                UserAppletAccessSchema,
                and_(
                    UserAppletAccessSchema.applet_id == AnswerSchema.applet_id,
                    UserAppletAccessSchema.user_id
                    == AnswerSchema.respondent_id,
                    UserAppletAccessSchema.role == Role.RESPONDENT,
                ),
            )
            .where(AnswerSchema.applet_id == applet_id, has_access)
            .order_by(
                AnswerItemSchema.created_at.desc(),
            )
        )
        if filters:
            query = query.where(*_AnswersExportFilter().get_clauses(**filters))

        res = await self._execute(query)
        answers = res.all()

        return parse_obj_as(list[UserAnswerData], answers)

    async def get_activity_history_by_ids(
        self, activity_hist_ids: list[str]
    ) -> list[ActivityHistory]:
        query: Query = (
            select(ActivityHistorySchema)
            .where(ActivityHistorySchema.id_version.in_(activity_hist_ids))
            .order_by(
                ActivityHistorySchema.applet_id, ActivityHistorySchema.order
            )
        )
        res = await self._execute(query)
        activities: list[ActivityHistorySchema] = res.scalars().all()

        return parse_obj_as(list[ActivityHistory], activities)

    async def get_item_history_by_activity_history(
        self, activity_hist_ids: list[str]
    ) -> list[ActivityItemHistory]:
        query: Query = (
            select(ActivityItemHistorySchema)
            .where(
                ActivityItemHistorySchema.activity_id.in_(activity_hist_ids)
            )
            .order_by(
                ActivityItemHistorySchema.activity_id,
                ActivityItemHistorySchema.order,
            )
        )
        res = await self._execute(query)
        items: list[ActivityItemHistorySchema] = res.scalars().all()

        return parse_obj_as(list[ActivityItemHistory], items)
