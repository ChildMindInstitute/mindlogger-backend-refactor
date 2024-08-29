import asyncio
import datetime
import uuid
from typing import Collection

from pydantic import parse_obj_as
from sqlalchemy import Text, and_, case, column, delete, func, null, or_, select, text, update
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import Query, aliased, contains_eager
from sqlalchemy.sql import Values
from sqlalchemy.sql.elements import BooleanClauseList

from apps.activities.db.schemas import ActivityHistorySchema, ActivityItemHistorySchema
from apps.activities.domain.activity_full import ActivityItemHistoryFull
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import (
    Answer,
    AnswerItemDataEncrypted,
    AppletCompletedEntities,
    CompletedEntity,
    FlowSubmission,
    FlowSubmissionInfo,
    IdentifierData,
    IdentifiersQueryParams,
    RespondentAnswerData,
    UserAnswerItemData,
)
from apps.answers.errors import AnswerNotFoundError
from apps.answers.filters import AppletSubmitDateFilter
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain.applet_history import Version
from apps.shared.filtering import Comparisons, FilterField, Filtering
from apps.shared.paging import paging
from infrastructure.database.crud import BaseCRUD


class _AnswersExportFilter(Filtering):
    respondent_ids = FilterField(AnswerItemSchema.respondent_id, method_name="filter_respondent_ids")

    def filter_respondent_ids(self, field, value):
        return and_(field.in_(value), AnswerItemSchema.is_assessment.isnot(True))

    target_subject_ids = FilterField(AnswerSchema.target_subject_id, Comparisons.IN)
    activity_history_ids = FilterField(AnswerSchema.activity_history_id, Comparisons.IN)
    from_date = FilterField(AnswerItemSchema.created_at, Comparisons.GREAT_OR_EQUAL)
    to_date = FilterField(AnswerItemSchema.created_at, Comparisons.LESS_OR_EQUAL)


class _AnswerListFilter(Filtering):
    respondent_ids = FilterField(AnswerItemSchema.respondent_id, method_name="filter_respondent_ids")
    target_subject_ids = FilterField(AnswerSchema.target_subject_id, Comparisons.IN)

    def filter_respondent_ids(self, field, value):
        if not value:
            return None
        return and_(field.in_(value), AnswerItemSchema.is_assessment.isnot(True))

    answer_id = FilterField(AnswerSchema.id)
    submit_id = FilterField(AnswerSchema.submit_id)
    applet_id = FilterField(AnswerSchema.applet_id)
    activity_id = FilterField(AnswerSchema.id_from_history_id(AnswerSchema.activity_history_id), cast=str)
    flow_id = FilterField(AnswerSchema.id_from_history_id(AnswerSchema.flow_history_id), cast=str)
    created_date = FilterField(func.date(AnswerItemSchema.created_at))


class _FlowSubmissionsFilter(Filtering):
    target_subject_id = FilterField(AnswerSchema.target_subject_id)
    applet_id = FilterField(AnswerSchema.applet_id)
    versions = FilterField(AnswerSchema.version, Comparisons.IN)


class _FlowSubmissionAggregateFilter(Filtering):
    from_datetime = FilterField(func.max(AnswerItemSchema.end_datetime), Comparisons.GREAT_OR_EQUAL)
    to_datetime = FilterField(func.max(AnswerItemSchema.end_datetime), Comparisons.LESS_OR_EQUAL)
    identifiers = FilterField(func.array_agg(AnswerItemSchema.identifier), method_name="filter_by_identifiers")
    is_completed = FilterField(func.bool_or(AnswerSchema.is_flow_completed), method_name="filter_completed")

    def filter_by_identifiers(self, field, values: list | None):
        return field.op("&&")(values)

    def filter_completed(self, field, value: bool | None):
        if value is True:
            return field.is_(True)
        return None


class AnswersCRUD(BaseCRUD[AnswerSchema]):
    schema_class = AnswerSchema

    async def create(self, schema: AnswerSchema):
        schema = await self._create(schema)
        return schema

    async def create_many(self, schemas: list[AnswerSchema]) -> list[AnswerSchema]:
        schemas = await self._create_many(schemas)
        return schemas

    async def get_list(self, **filters) -> list[Answer]:
        """
        @param filters: see supported filters: _AnswerListFilter
        """
        query = select(AnswerSchema).join(AnswerSchema.answer_item).options(contains_eager(AnswerSchema.answer_item))

        _filters = _AnswerListFilter().get_clauses(**filters)
        if _filters:
            query = query.where(*_filters)

        res = await self._execute(query)
        data = res.unique().scalars().all()

        return parse_obj_as(list[Answer], data)

    async def get_flow_submission_data(
        self, *, created_date: datetime.date | None = None, **filters
    ) -> list[FlowSubmissionInfo]:
        """
        @param created_date: submission max answer date
        @param filters: see supported filters: _AnswerListFilter
        """
        created_at = func.max(AnswerItemSchema.created_at)
        query = (
            select(
                AnswerSchema.submit_id,
                AnswerSchema.flow_history_id,
                AnswerSchema.applet_id,
                AnswerSchema.version,
                created_at.label("created_at"),
                func.max(AnswerItemSchema.end_datetime).label("end_datetime"),
            )
            .join(AnswerSchema.answer_item)
            .where(AnswerSchema.flow_history_id.isnot(None))
            .group_by(
                AnswerSchema.submit_id, AnswerSchema.flow_history_id, AnswerSchema.applet_id, AnswerSchema.version
            )
            .order_by(created_at)
            .having(func.bool_or(AnswerSchema.is_flow_completed.is_(True)))  # completed submissions only
        )

        _filters = _AnswerListFilter().get_clauses(**filters)
        if _filters:
            query = query.where(*_filters)
        if created_date:
            query = query.having(func.date(created_at) == created_date)

        res = await self._execute(query)
        data = res.all()

        return parse_obj_as(list[FlowSubmissionInfo], data)

    async def get_flow_submissions(
        self, applet_id: uuid.UUID, flow_id: uuid.UUID, *, page=None, limit=None, **filters
    ) -> tuple[list[FlowSubmission], int]:
        created_at = func.max(AnswerItemSchema.created_at)
        query = (
            select(
                AnswerSchema.submit_id,
                AnswerSchema.flow_history_id,
                AnswerSchema.applet_id,
                AnswerSchema.version,
                created_at.label("created_at"),
                func.max(AnswerItemSchema.end_datetime).label("end_datetime"),
                func.bool_or(AnswerSchema.is_flow_completed).is_(True).label("is_completed"),
                # fmt: off
                func.array_agg(
                    func.json_build_object(
                        text("'id'"),
                        AnswerSchema.id,
                        text("'submit_id'"),
                        AnswerSchema.submit_id,
                        text("'version'"),
                        AnswerSchema.version,
                        text("'activity_history_id'"),
                        AnswerSchema.activity_history_id,
                        text("'flow_history_id'"),
                        AnswerSchema.flow_history_id,
                        text("'user_public_key'"),
                        AnswerItemSchema.user_public_key,
                        text("'answer'"),
                        AnswerItemSchema.answer,
                        text("'events'"),
                        AnswerItemSchema.events,
                        text("'item_ids'"),
                        AnswerItemSchema.item_ids,
                        text("'identifier'"),
                        AnswerItemSchema.identifier,
                        text("'migrated_data'"),
                        AnswerItemSchema.migrated_data,
                        text("'end_datetime'"),
                        AnswerItemSchema.end_datetime,
                        text("'created_at'"),
                        AnswerItemSchema.created_at,
                    )
                ).label("answers"),
                # fmt: on
            )
            .join(AnswerSchema.answer_item)
            .where(
                AnswerSchema.id_from_history_id(AnswerSchema.flow_history_id) == str(flow_id),
                AnswerSchema.applet_id == applet_id,
            )
            .group_by(
                AnswerSchema.submit_id, AnswerSchema.flow_history_id, AnswerSchema.applet_id, AnswerSchema.version
            )
        )

        _filters = _FlowSubmissionsFilter().get_clauses(**filters)
        if _filters:
            query = query.where(*_filters)

        _filters = _FlowSubmissionAggregateFilter().get_clauses(**filters)
        if _filters:
            query = query.having(and_(*_filters))

        query_data = query.order_by(created_at)
        query_data = paging(query_data, page, limit)

        query_count = select(func.count()).select_from(query.with_only_columns(AnswerSchema.submit_id).subquery())

        coro_data = self._execute(query_data)
        coro_count = self._execute(query_count)
        result_data, result_count = await asyncio.gather(coro_data, coro_count)

        data = result_data.all()
        count = result_count.scalar()

        return parse_obj_as(list[FlowSubmission], data), count

    async def get_respondents_submit_dates(
        self, applet_id: uuid.UUID, filters: AppletSubmitDateFilter
    ) -> list[datetime.date]:
        query: Query = select(func.date(AnswerSchema.created_at))
        query = query.where(func.date(AnswerSchema.created_at) >= filters.from_date)
        query = query.where(func.date(AnswerSchema.created_at) <= filters.to_date)
        query = query.where(AnswerSchema.applet_id == applet_id)
        if filters.respondent_id:
            query = query.where(AnswerSchema.respondent_id == filters.respondent_id)
        if filters.target_subject_id:
            query = query.where(AnswerSchema.target_subject_id == filters.target_subject_id)
        query = query.order_by(AnswerSchema.created_at.asc())
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_answers_by_applet_respondent(
        self,
        respondent_id: uuid.UUID | None,
        applet_id: uuid.UUID,
    ) -> list[AnswerSchema]:
        if not respondent_id:
            return []
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.respondent_id == respondent_id)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_id(self, id_: uuid.UUID) -> AnswerSchema:
        schema = await self._get("id", id_)
        if not schema:
            raise AnswerNotFoundError()
        return schema

    async def delete_by_applet_user(self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None = None):
        query: Query = delete(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        if respondent_id:
            query = query.where(AnswerSchema.respondent_id == respondent_id)
        await self._execute(query)

    @classmethod
    def _exclude_assessment_val(cls, col):
        return case(
            (AnswerItemSchema.is_assessment.is_(True), null()),
            else_=col,
        )

    async def get_applet_answers(
        self,
        applet_id: uuid.UUID,
        *,
        include_assessments: bool = True,
        page=None,
        limit=None,
        **filters,
    ) -> tuple[list[RespondentAnswerData], int]:
        reviewed_answer_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerSchema.id),
            else_=null(),
        )

        record_id = case(
            (AnswerItemSchema.is_assessment.is_(True), AnswerItemSchema.id),
            else_=AnswerSchema.id,
        )

        activity_history_id = case(
            (
                AnswerItemSchema.is_assessment.is_(True),
                AnswerItemSchema.assessment_activity_id,
            ),
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
                AnswerSchema.migrated_data,
                AnswerItemSchema.user_public_key,
                AnswerItemSchema.respondent_id,
                self._exclude_assessment_val(AnswerSchema.target_subject_id).label("target_subject_id"),
                self._exclude_assessment_val(AnswerSchema.source_subject_id).label("source_subject_id"),
                self._exclude_assessment_val(AnswerSchema.relation).label("relation"),
                AnswerItemSchema.answer,
                AnswerItemSchema.events,
                AnswerItemSchema.item_ids,
                AnswerItemSchema.scheduled_datetime,
                AnswerItemSchema.start_datetime,
                AnswerItemSchema.end_datetime,
                AnswerItemSchema.migrated_date,
                AnswerSchema.applet_history_id,
                activity_history_id.label("activity_history_id"),
                flow_history_id.label("flow_history_id"),
                AnswerItemSchema.created_at,
                reviewed_answer_id.label("reviewed_answer_id"),
                AnswerItemSchema.reviewed_flow_submit_id,
                AnswerSchema.client,
                AnswerItemSchema.tz_offset,
                AnswerItemSchema.scheduled_event_id,
            )
            .select_from(AnswerSchema)
            .join(AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id)
            .where(
                AnswerSchema.applet_id == applet_id,
                *filter_clauses,
            )
        )

        if not include_assessments:
            query = query.where(AnswerItemSchema.is_assessment.isnot(True))

        query_count = query.with_only_columns(func.count())

        query = query.order_by(AnswerItemSchema.created_at.desc())
        query = paging(query, page, limit)
        coro_data, coro_count = (
            self._execute(query),
            self._execute(query_count),
        )

        res, res_count = await asyncio.gather(coro_data, coro_count)
        answers = res.all()

        total = res_count.scalars().one()

        return parse_obj_as(list[RespondentAnswerData], answers), total

    async def get_item_history_by_activity_history(self, activity_hist_ids: list[str]) -> list[ActivityItemHistoryFull]:
        query: Query = (
            select(ActivityItemHistorySchema)
            .where(ActivityItemHistorySchema.activity_id.in_(activity_hist_ids))
            .order_by(
                ActivityItemHistorySchema.activity_id,
                ActivityItemHistorySchema.order,
            )
        )
        res = await self._execute(query)
        items: list[ActivityItemHistorySchema] = res.scalars().all()

        return parse_obj_as(list[ActivityItemHistoryFull], items)

    async def get_identifiers_by_activity_id(
        self,
        activity_hist_ids: Collection[str],
        filters: IdentifiersQueryParams,
    ) -> list[tuple[str, str, dict, datetime.datetime]]:
        query: Query = select(
            AnswerItemSchema.identifier,
            AnswerItemSchema.user_public_key,
            AnswerItemSchema.migrated_data,
            func.max(AnswerSchema.created_at),
        )
        query = query.join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
        query = query.group_by(
            AnswerItemSchema.identifier, AnswerItemSchema.user_public_key, AnswerItemSchema.migrated_data
        )
        query = query.where(
            AnswerItemSchema.identifier.isnot(None),
            AnswerSchema.activity_history_id.in_(activity_hist_ids),
        )
        if filters.target_subject_id:
            query = query.where(AnswerSchema.target_subject_id == filters.target_subject_id)
        if filters.respondent_id:
            query = query.where(AnswerSchema.respondent_id == filters.respondent_id)
        if filters.answer_id:
            query = query.where(AnswerItemSchema.answer_id == filters.answer_id)

        db_result = await self._execute(query)

        return db_result.all()  # noqa

    async def get_versions_by_activity_id(self, activity_id: uuid.UUID) -> list[Version]:
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

    async def get_latest_activity_answer(
        self,
        applet_id: uuid.UUID,
        activity_history_ids: Collection[str],
        target_subject_id: uuid.UUID,
    ) -> AnswerSchema | None:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.activity_history_id.in_(activity_history_ids))
        query = query.where(AnswerSchema.target_subject_id == target_subject_id)
        query = query.order_by(AnswerSchema.created_at.desc())
        query = query.limit(1)

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_latest_answer_by_activity_id(
        self, applet_id: uuid.UUID, activity_id: uuid.UUID
    ) -> AnswerSchema | None:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(func.split_part(AnswerSchema.activity_history_id, "_", 1) == str(activity_id))
        query = query.order_by(AnswerSchema.created_at.desc())
        query = query.limit(1)

        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def get_latest_flow_answer(
        self,
        applet_id: uuid.UUID,
        flow_history_ids: Collection[str],
        target_subject_id: uuid.UUID,
    ) -> AnswerSchema:
        query: Query = select(AnswerSchema)
        query = query.where(
            AnswerSchema.applet_id == applet_id,
            AnswerSchema.flow_history_id.in_(flow_history_ids),
            AnswerSchema.target_subject_id == target_subject_id,
            AnswerSchema.is_flow_completed.is_(True),
        )
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
        query = query.order_by(AnswerSchema.created_at.asc(), AnswerSchema.updated_at)
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_applet_activity_created_at(
        self,
        applet_id: uuid.UUID,
        activity_id: str,
        created_at: int,
        user_id: uuid.UUID | None = None,
        submit_id: uuid.UUID | None = None,
    ) -> list[AnswerSchema]:
        # TODO: investigate this later
        created_time = datetime.datetime.fromtimestamp(created_at)
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.created_at == created_time)
        query = query.filter(AnswerSchema.activity_history_id.startswith(activity_id))
        if submit_id:
            query = query.where(AnswerSchema.submit_id == submit_id)
        if user_id:
            query = query.where(AnswerSchema.respondent_id == user_id)

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_submitted_activity_with_last_date(
        self,
        activity_hist_ids: list[str],
        respondent_id: uuid.UUID | None,
        subject_id: uuid.UUID | None,
    ) -> list[tuple[str, datetime.datetime]]:
        activity_ids = set(map(lambda id_version: id_version.split("_")[0], activity_hist_ids))
        query: Query = select(AnswerSchema.activity_history_id, func.max(AnswerSchema.created_at))
        query = query.where(or_(*(AnswerSchema.activity_history_id.like(f"{item}_%") for item in activity_ids)))
        if respondent_id:
            query = query.where(AnswerSchema.respondent_id == respondent_id)
        if subject_id:
            query = query.where(AnswerSchema.target_subject_id == subject_id)
        query = query.group_by(AnswerSchema.activity_history_id)
        query = query.order_by(AnswerSchema.activity_history_id)
        query = query.order_by(AnswerSchema.activity_history_id)
        db_result = await self._execute(query)
        return db_result.all()  # noqa

    async def get_submitted_flows_with_last_date(
        self, applet_id: uuid.UUID, target_subject_id: uuid.UUID | None
    ) -> list[tuple[str, datetime.datetime]]:
        subquery: Query = select(AnswerSchema.submit_id)
        subquery = subquery.where(
            AnswerSchema.applet_id == applet_id,
            AnswerSchema.flow_history_id.isnot(None),
            AnswerSchema.is_flow_completed.is_(True),
        )
        if target_subject_id:
            subquery = subquery.where(AnswerSchema.target_subject_id == target_subject_id)

        query: Query = select(AnswerSchema.flow_history_id, func.max(AnswerSchema.created_at))
        query = query.where(
            AnswerSchema.submit_id.in_(subquery),
            AnswerSchema.is_flow_completed.is_(True),
        )
        query = query.group_by(AnswerSchema.flow_history_id)
        query = query.order_by(AnswerSchema.flow_history_id)
        db_result = await self._execute(query)
        return db_result.all()  # noqa

    async def get_completed_answers_data(
        self,
        applet_id: uuid.UUID,
        version: str,
        respondent_id: uuid.UUID,
        from_date: datetime.date,
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
            .join(AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id)
            .where(
                AnswerSchema.applet_id == applet_id,
                AnswerSchema.version == version,
                AnswerSchema.respondent_id == respondent_id,
                AnswerItemSchema.local_end_date >= from_date,
                is_completed,
            )
            .order_by(
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
                AnswerItemSchema.local_end_date.desc(),
                AnswerItemSchema.local_end_time.desc(),
            )
            .distinct(
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
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
                activities.append(CompletedEntity(**row, id=row.activity_history_id))

        return AppletCompletedEntities(
            id=applet_id,
            version=version,
            activities=activities,
            activity_flows=flows,
        )

    async def get_completed_answers_data_list(
        self,
        applets_version_map: dict[uuid.UUID, str],
        respondent_id: uuid.UUID,
        from_date: datetime.date,
    ) -> list[AppletCompletedEntities]:
        is_completed = or_(
            AnswerSchema.is_flow_completed,
            AnswerSchema.flow_history_id.is_(None),
        )

        applet_version_filter_list: list[BooleanClauseList] = list()
        for applet_id, version in applets_version_map.items():
            applet_version_filter_list.append(
                and_(
                    AnswerSchema.applet_id == applet_id,
                    AnswerSchema.version == version,
                )
            )
        applet_version_filter: BooleanClauseList = or_(*applet_version_filter_list)

        query: Query = (
            select(
                AnswerSchema.id.label("answer_id"),
                AnswerSchema.applet_id,
                AnswerSchema.submit_id,
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
                AnswerItemSchema.local_end_date,
                AnswerItemSchema.local_end_time,
            )
            .join(AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id)
            .where(
                AnswerSchema.respondent_id == respondent_id,
                AnswerItemSchema.local_end_date >= from_date,
                is_completed,
            )
            .where(applet_version_filter)
            .order_by(
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
                AnswerItemSchema.local_end_date.desc(),
                AnswerItemSchema.local_end_time.desc(),
            )
            .distinct(
                AnswerSchema.activity_history_id,
                AnswerSchema.flow_history_id,
                AnswerItemSchema.scheduled_event_id,
            )
        )

        db_result = await self._execute(query)
        data = db_result.all()

        applet_activities_flows_map: dict[uuid.UUID, dict[str, list]] = dict()
        for row in data:
            applet_activities_flows_map.setdefault(row.applet_id, {"activities": [], "flows": []})
            if row.flow_history_id:
                applet_activities_flows_map[row.applet_id]["flows"].append(
                    CompletedEntity(**row, id=row.flow_history_id)
                )
            else:
                applet_activities_flows_map[row.applet_id]["activities"].append(
                    CompletedEntity(**row, id=row.activity_history_id)
                )

        result_list: list[AppletCompletedEntities] = list()
        for applet_id, version in applets_version_map.items():
            result_list.append(
                AppletCompletedEntities(
                    id=applet_id,
                    version=version,
                    activities=applet_activities_flows_map.get(applet_id, {"activities": [], "flows": []})[
                        "activities"
                    ],
                    activity_flows=applet_activities_flows_map.get(applet_id, {"activities": [], "flows": []})["flows"],
                )
            )

        return result_list

    async def get_latest_applet_version(self, applet_id: uuid.UUID) -> str:
        query: Query = select(AnswerSchema.applet_history_id)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.order_by(AnswerSchema.version.desc())
        query = query.limit(1)
        db_result = await self._execute(query)
        res = db_result.first()
        return res[0] if res else None

    async def get_applet_user_answer_items(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, page=None, limit=None
    ) -> list[UserAnswerItemData]:
        query: Query = (
            select(
                AnswerItemSchema.id,
                AnswerItemSchema.user_public_key,
                AnswerItemSchema.answer,
                AnswerItemSchema.events,
                AnswerItemSchema.identifier,
                AnswerItemSchema.migrated_data,
            )
            .select_from(AnswerSchema)
            .join(AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id)
            .where(
                AnswerSchema.applet_id == applet_id,
                AnswerItemSchema.respondent_id == user_id,
            )
            .order_by(AnswerItemSchema.id)
        )
        query = paging(query, page, limit)

        db_result = await self._execute(query)

        return parse_obj_as(list[UserAnswerItemData], db_result.all())

    async def update_encrypted_fields(self, user_public_key: str, data: list[AnswerItemDataEncrypted]):
        if data:
            vals = Values(
                column("id", UUID(as_uuid=True)),
                column("answer", Text),
                column("events", Text),
                column("identifier", Text),
                name="answer_data",
            ).data([(row.id, row.answer, row.events, row.identifier) for row in data])
            query = (
                update(AnswerItemSchema)
                .where(AnswerItemSchema.id == vals.c.id)
                .values(
                    answer=vals.c.answer,
                    events=vals.c.events,
                    identifier=vals.c.identifier,
                    user_public_key=user_public_key,
                )
            )

            await self._execute(query)

    async def is_single_report_flow(self, answer_flow_id: str | None) -> bool:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.id_version == answer_flow_id)
        db_result = await self._execute(query)
        db_result = db_result.first()
        flow_history_schema = db_result[0] if db_result else None  # type: ActivityFlowHistoriesSchema | None
        if not flow_history_schema:
            return False
        return flow_history_schema.is_single_report

    async def get_last_answer_dates(
        self, subject_ids: list[uuid.UUID], applet_id: uuid.UUID | None
    ) -> dict[uuid.UUID, datetime.datetime]:
        query: Query = (
            select(
                AnswerSchema.target_subject_id,
                func.max(AnswerSchema.created_at),
            )
            .group_by(AnswerSchema.target_subject_id)
            .where(AnswerSchema.target_subject_id.in_(subject_ids))
        )
        if applet_id:
            query = query.where(AnswerSchema.applet_id == applet_id)
        result = await self._execute(query)
        return {t[0]: t[1] for t in result.all()}

    async def delete_by_subject(self, subject_id: uuid.UUID):
        query: Query = delete(AnswerSchema).where(
            or_(AnswerSchema.target_subject_id == subject_id, AnswerSchema.source_subject_id == subject_id)
        )
        await self._execute(query)

    async def get_flow_identifiers(
        self, applet_id: uuid.UUID, flow_id: uuid.UUID, target_subject_id: uuid.UUID
    ) -> list[IdentifierData]:
        completed_submission = aliased(AnswerSchema, name="completed_submission")
        is_submission_completed = (
            select(completed_submission.submit_id)
            .where(
                completed_submission.submit_id == AnswerSchema.submit_id,
                completed_submission.is_flow_completed.is_(True),
            )
            .exists()
        )
        query = (
            select(
                AnswerItemSchema.identifier,
                AnswerItemSchema.user_public_key,
                AnswerItemSchema.is_identifier_encrypted.label("is_encrypted"),  # type: ignore[attr-defined]
                func.max(AnswerItemSchema.created_at).label("last_answer_date"),
            )
            .select_from(AnswerSchema)
            .join(AnswerSchema.answer_item)
            .where(
                AnswerSchema.applet_id == applet_id,
                AnswerSchema.id_from_history_id(AnswerSchema.flow_history_id) == str(flow_id),
                AnswerSchema.target_subject_id == target_subject_id,
                AnswerItemSchema.identifier.isnot(None),
                is_submission_completed,
            )
            .group_by(
                AnswerItemSchema.identifier,
                AnswerItemSchema.user_public_key,
                AnswerItemSchema.is_identifier_encrypted,
            )
            .order_by(column("last_answer_date"))
        )

        result = await self._execute(query)
        data = result.all()

        return parse_obj_as(list[IdentifierData], data)

    async def replace_answers_subject(self, subject_id_from: uuid.UUID, subject_id_to: uuid.UUID):
        new_target_subject_id = case(
            (AnswerSchema.target_subject_id == subject_id_from, subject_id_to),
            else_=AnswerSchema.target_subject_id,
        )
        new_source_subject_id = case(
            (AnswerSchema.source_subject_id == subject_id_from, subject_id_to),
            else_=AnswerSchema.source_subject_id,
        )

        query = (
            update(AnswerSchema)
            .where(
                or_(
                    AnswerSchema.target_subject_id == subject_id_from,
                    AnswerSchema.source_subject_id == subject_id_from,
                )
            )
            .values(
                target_subject_id=new_target_subject_id,
                source_subject_id=new_source_subject_id,
            )
        )

        await self._execute(query)

    async def get_last_answer_in_flow(
        self, submit_id: uuid.UUID, flow_id: uuid.UUID | None = None
    ) -> AnswerSchema | None:
        query = select(AnswerSchema)
        query = query.where(
            AnswerSchema.submit_id == submit_id,
            AnswerSchema.is_flow_completed.is_(True),
        )
        if flow_id:
            query = query.where(AnswerSchema.flow_history_id.like(f"{flow_id}_%"))
        result = await self._execute(query)
        return result.scalar_one_or_none()

    async def get_applet_answer_rows(self, applet_id: uuid.UUID):
        query = select(AnswerSchema.__table__).where(AnswerSchema.applet_id == applet_id)
        res = await self._execute(query)
        return res.all()

    async def get_applet_answers_total(self, applet_id: uuid.UUID):
        query = select(func.count(AnswerSchema.id)).where(AnswerSchema.applet_id == applet_id)
        res = await self._execute(query)
        return res.scalar()

    async def get_applet_answer_item_rows(self, applet_id: uuid.UUID):
        query = (
            select(AnswerItemSchema.__table__)
            .join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
            .where(AnswerSchema.applet_id == applet_id)
        )

        res = await self._execute(query)
        return res.all()

    async def get_applet_answer_items_total(self, applet_id: uuid.UUID):
        query = (
            select(func.count(AnswerItemSchema.id))
            .join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
            .where(AnswerSchema.applet_id == applet_id)
        )

        res = await self._execute(query)
        return res.scalar()

    async def insert_answers_batch(self, values):
        insert_query = (
            insert(AnswerSchema)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[AnswerSchema.id],
            )
        )
        await self._execute(insert_query)

    async def insert_answer_items_batch(self, values):
        insert_query = (
            insert(AnswerItemSchema)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[AnswerItemSchema.id],
            )
        )
        await self._execute(insert_query)

    async def get_answers_respondents(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        query = (
            select(AnswerItemSchema.respondent_id)
            .join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
            .where(AnswerSchema.applet_id == applet_id)
            .distinct()
        )
        res = await self._execute(query)
        user_ids = res.scalars().all()
        return user_ids

    async def delete_by_ids(self, ids: list[uuid.UUID]):
        query: Query = delete(AnswerSchema)
        query = query.where(AnswerSchema.id.in_(ids))
        await self._execute(query)
