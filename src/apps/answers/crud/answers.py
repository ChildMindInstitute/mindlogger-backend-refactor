import datetime
import uuid

from pydantic import parse_obj_as
from sqlalchemy import and_, case, delete, func, null, or_, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activities.domain import ActivityHistory
from apps.activities.domain.activity_full import ActivityItemHistoryFull
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import (
    AppletCompletedEntities,
    CompletedEntity,
    RespondentAnswerData,
    Version,
)
from apps.answers.errors import AnswerNotFoundError
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.paging import paging
from infrastructure.database.crud import BaseCRUD


class _AnswersExportFilter(Filtering):
    respondent_ids = FilterField(
        AnswerItemSchema.respondent_id, method_name="filter_respondent_ids"
    )

    def filter_respondent_ids(self, field, value):
        return and_(
            field.in_(value), AnswerItemSchema.is_assessment.isnot(True)
        )

    activity_history_ids = FilterField(
        AnswerSchema.activity_history_id, Comparisons.IN
    )
    from_date = FilterField(
        AnswerItemSchema.created_at, Comparisons.GREAT_OR_EQUAL
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
        self,
        applet_id: uuid.UUID,
        *,
        include_assessments: bool = True,
        page=None,
        limit=None,
        **filters,
    ) -> list[RespondentAnswerData]:

        reviewed_answer_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerSchema.id),
            else_=null(),
        )

        record_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerItemSchema.id),
            else_=AnswerSchema.id,
        )

        activity_history_id = case(
            (AnswerItemSchema.is_assessment.is_(True), null()),
            else_=AnswerSchema.activity_history_id,
        )

        flow_history_id = case(
            (AnswerItemSchema.is_assessment.is_(True), null()),
            else_=AnswerSchema.flow_history_id,
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
                AnswerItemSchema.answer,
                AnswerItemSchema.events,
                AnswerItemSchema.item_ids,
                AnswerItemSchema.scheduled_datetime,
                AnswerItemSchema.start_datetime,
                AnswerItemSchema.end_datetime,
                AnswerSchema.applet_history_id,
                activity_history_id.label("activity_history_id"),
                flow_history_id.label("flow_history_id"),
                AnswerItemSchema.created_at,
                reviewed_answer_id.label("reviewed_answer_id"),
            )
            .select_from(AnswerSchema)
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
            .where(
                AnswerSchema.applet_id == applet_id,
                *filter_clauses,
            )
            .order_by(AnswerItemSchema.created_at.desc())
        )
        query = paging(query, page, limit)

        if not include_assessments:
            query = query.where(AnswerItemSchema.is_assessment.isnot(True))

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

    async def get_by_applet_activity_created_at(
        self, applet_id: uuid.UUID, activity_id: str, created_at: int
    ) -> list[AnswerSchema] | None:
        created_time = datetime.datetime.fromtimestamp(created_at)
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.created_at == created_time)
        query = query.filter(
            AnswerSchema.activity_history_id.startswith(activity_id)
        )
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
        self, answer_id: uuid.UUID
    ) -> tuple[AnswerSchema, AppletHistorySchema, ActivityHistorySchema]:
        query: Query = select(
            AnswerSchema,
            AppletSchema,
            ActivityHistorySchema,
        )
        query = query.join(
            AppletSchema,
            AppletSchema.id == AnswerSchema.applet_id,
            isouter=True,
        )
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version
            == AnswerSchema.activity_history_id,
            isouter=True,
        )
        query = query.where(AnswerItemSchema.is_assessment == False)  # noqa
        query = query.where(AnswerSchema.id == answer_id)

        db_result = await self._execute(query)
        return db_result.first()

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

    async def get_completed_answers_data(
        self,
        applet_id: uuid.UUID,
        version: str,
        respondent_id: uuid.UUID,
        date: datetime.date,
    ) -> AppletCompletedEntities:
        is_completed = or_(
            AnswerSchema.is_flow_completed,
            AnswerSchema.flow_history_id.is_(None),
        )

        query: Query = (
            select(
                AnswerSchema.id.label("answer_id"),
                AnswerSchema.submit_id,
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
                AnswerItemSchema.local_end_date,
                AnswerItemSchema.local_end_time,
            )
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
            .where(
                AnswerSchema.applet_id == applet_id,
                AnswerSchema.version == version,
                AnswerSchema.respondent_id == respondent_id,
                AnswerItemSchema.local_end_date == date,
                is_completed,
            )
            .order_by(
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.local_end_time.desc(),
            )
            .distinct(
                AnswerSchema.activity_history_id, AnswerSchema.flow_history_id
            )
        )

        db_result = await self._execute(query)
        data = db_result.all()

        activities = []
        flows = []
        for row in data:
            if row.flow_history_id:
                flows.append(CompletedEntity(**row, id=row.flow_history_id))
            else:
                activities.append(
                    CompletedEntity(**row, id=row.activity_history_id)
                )

        return AppletCompletedEntities(
            id=applet_id,
            version=version,
            activities=activities,
            activity_flows=flows,
        )
