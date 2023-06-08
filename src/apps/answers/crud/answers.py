import datetime
import uuid

from pydantic import parse_obj_as
from sqlalchemy import (  # true,
    and_,
    any_,
    case,
    delete,
    exists,
    func,
    literal_column,
    null,
    or_,
    select,
    text,
    true,
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
from apps.answers.domain import RespondentAnswerData
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.query_params import QueryParams
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD


class _AnswersExportFilter(Filtering):
    respondent_ids = FilterField(AnswerSchema.respondent_id, Comparisons.IN)


class _IdentifierFilter(Filtering):
    from_datetime = FilterField(
        AnswerItemSchema.created_at, Comparisons.GREAT_OR_EQUAL
    )
    to_datetime = FilterField(
        AnswerItemSchema.created_at, Comparisons.LESS_OR_EQUAL
    )


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
    ) -> list[RespondentAnswerData]:
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
                        AnswerItemSchema.is_assessment.isnot(True),
                        UserAppletAccessSchema.role == Role.REVIEWER,
                        AnswerSchema.respondent_id
                        == any_(assigned_respondents.scalar_subquery()),
                    ),
                ),
            )
            .correlate(AnswerSchema, AnswerItemSchema)
        )

        is_manager = case(
            (AnswerItemSchema.is_assessment.is_(True), true()),
            else_=(
                exists()
                .where(
                    UserAppletAccessSchema.user_id == UserSchema.id,
                    UserAppletAccessSchema.applet_id == AnswerSchema.applet_id,
                    UserAppletAccessSchema.role != Role.RESPONDENT,
                )
                .correlate(AnswerSchema, UserSchema)
            ),
        )

        reviewed_answer_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerSchema.id),
            else_=null(),
        )

        record_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerItemSchema.id),
            else_=AnswerSchema.id,
        )

        filter_clauses = []
        if filters:
            filter_clauses = _AnswersExportFilter().get_clauses(**filters)

        query: Query = (
            select(
                record_id.label("id"),
                AnswerSchema.submit_id,
                AnswerSchema.version,
                AnswerItemSchema.user_public_key,
                AnswerItemSchema.respondent_id,
                UserAppletAccessSchema.respondent_secret_id,
                UserSchema.email.label("respondent_email"),
                is_manager.label("is_manager"),
                AnswerItemSchema.answer,
                AnswerItemSchema.events,
                AnswerItemSchema.item_ids,
                AnswerSchema.applet_history_id,
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                ActivityFlowHistoriesSchema.name.label("flow_name"),
                AnswerItemSchema.created_at,
                reviewed_answer_id.label("reviewed_answer_id"),
            )
            .select_from(AnswerSchema)
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
            .outerjoin(
                ActivityFlowHistoriesSchema,
                ActivityFlowHistoriesSchema.id_version
                == AnswerSchema.flow_history_id,
            )
            .outerjoin(UserSchema, UserSchema.id == AnswerSchema.respondent_id)
            .outerjoin(
                UserAppletAccessSchema,
                and_(
                    AnswerItemSchema.is_assessment.isnot(True),
                    UserAppletAccessSchema.applet_id == AnswerSchema.applet_id,
                    UserAppletAccessSchema.user_id
                    == AnswerItemSchema.respondent_id,
                    UserAppletAccessSchema.role == Role.RESPONDENT,
                ),
            )
            .where(
                AnswerSchema.applet_id == applet_id,
                has_access,
                *filter_clauses,
            )
            .order_by(AnswerItemSchema.created_at.desc())
        )

        res = await self._execute(query)
        answers = res.all()

        return parse_obj_as(list[RespondentAnswerData], answers)

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

    async def get_identifiers_by_activity_id(
        self, activity_id: uuid.UUID, query_params: QueryParams
    ) -> list[str]:
        query: Query = select(AnswerItemSchema.identifier)
        query = query.distinct(AnswerItemSchema.identifier)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == AnswerItemSchema.activity_history_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        if query_params.filters:
            query = query.where(
                *_IdentifierFilter().get_clauses(**query_params.filters)
            )

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_versions_by_activity_id(
        self, activity_id: uuid.UUID, query_params: QueryParams
    ) -> list[str]:
        query: Query = select(AnswerSchema.version)
        query = query.join(
            AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
        )
        query = query.distinct(AnswerSchema.version)
        query = query.where(ActivityHistorySchema.id == activity_id)
        if query_params.filters:
            query = query.where(
                *_IdentifierFilter().get_clauses(**query_params.filters)
            )

        db_result = await self._execute(query)

        return db_result.scalars().all()
