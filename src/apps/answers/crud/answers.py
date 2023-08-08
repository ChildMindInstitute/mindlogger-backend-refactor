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
from apps.activities.domain.activity_full import ActivityItemHistoryFull
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import RespondentAnswerData, Version
from apps.answers.errors import AnswerNotFoundError
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD


class _AnswersExportFilter(Filtering):
    respondent_ids = FilterField(AnswerSchema.respondent_id, Comparisons.IN)


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
                AnswerItemSchema.scheduled_datetime,
                AnswerItemSchema.start_datetime,
                AnswerItemSchema.end_datetime,
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
    ) -> list[ActivityItemHistoryFull]:
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

        return parse_obj_as(list[ActivityItemHistoryFull], items)

    async def get_identifiers_by_activity_id(
        self, activity_id: uuid.UUID
    ) -> list[tuple[str, str]]:
        query: Query = select(
            AnswerItemSchema.identifier, AnswerItemSchema.user_public_key
        )
        query = query.distinct(AnswerItemSchema.identifier)
        query = query.where(AnswerItemSchema.identifier != None)  # noqa: E711
        query = query.join(
            AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id
        )
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == AnswerSchema.activity_history_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        db_result = await self._execute(query)

        return db_result.all()

    async def get_versions_by_activity_id(
        self, activity_id: uuid.UUID
    ) -> list[Version]:
        query: Query = select(
            ActivityHistorySchema.id,
            AppletHistorySchema.version,
            AppletHistorySchema.created_at,
        )
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
        )
        query = query.where(ActivityHistorySchema.id == activity_id)
        query = query.order_by(AppletHistorySchema.created_at.asc())
        db_result = await self._execute(query)
        results = []
        for _, version, created_at in db_result.all():
            results.append(Version(version=version, created_at=created_at))

        return results

    async def get_latest_answer(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        respond_id: uuid.UUID,
    ) -> AnswerSchema | None:
        query: Query = select(AnswerSchema)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == AnswerSchema.activity_history_id,
        )
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(ActivityHistorySchema.id == activity_id)
        query = query.where(AnswerItemSchema.respondent_id == respond_id)
        query = query.order_by(AnswerSchema.created_at.desc())
        query = query.limit(1)

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_by_submit_id(
        self, submit_id: uuid.UUID, answer_id: uuid.UUID | None = None
    ) -> list[AnswerSchema] | None:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.submit_id == submit_id)
        if answer_id:
            query = query.where(AnswerSchema.id == answer_id)
        query = query.order_by(AnswerSchema.created_at.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_activity_flow_by_answer_id(
        self, answer_id: uuid.UUID
    ) -> bool:
        query: Query = select(AnswerItemSchema, ActivityFlowHistoriesSchema)
        query = query.join(
            AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id
        )
        query = query.join(
            ActivityFlowHistoriesSchema,
            ActivityFlowHistoriesSchema.id_version
            == AnswerSchema.flow_history_id,
            isouter=True,
        )
        query = query.where(AnswerItemSchema.is_assessment == False)  # noqa
        query = query.where(AnswerSchema.id == answer_id)

        db_result = await self._execute(query)
        (
            _,
            flow_history_schema,
        ) = (
            db_result.first()
        )  # type: AnswerItemSchema, ActivityFlowHistoriesSchema
        if not flow_history_schema:
            return False
        return flow_history_schema.is_single_report

    async def get_applet_info_by_answer_id(
        self, answer: AnswerSchema
    ) -> tuple[AppletHistorySchema, ActivityHistorySchema]:
        query: Query = select(
            AppletSchema,
            ActivityHistorySchema,
        )
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id == AppletSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.applet_id == AppletHistorySchema.id_version,
            isouter=True,
        )
        db_result = await self._execute(query)
        res = db_result.first()
        return res

    async def get_activities_which_has_answer(
        self, activity_ids: list[uuid.UUID], respondent_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        query: Query = select(AnswerSchema.id, ActivityHistorySchema.id)
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == AnswerSchema.activity_history_id,
        )
        query = query.where(ActivityHistorySchema.id.in_(activity_ids))
        if respondent_id:
            query = query.where(AnswerSchema.respondent_id == respondent_id)

        db_result = await self._execute(query)
        results = []
        for answer_id, activity_id in db_result.all():
            results.append(activity_id)
        return results
