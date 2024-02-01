import asyncio
import datetime
import uuid
from typing import Collection

from pydantic import parse_obj_as
from sqlalchemy import (
    Text,
    and_,
    case,
    column,
    delete,
    func,
    null,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Query
from sqlalchemy.sql import Values
from sqlalchemy.sql.elements import BooleanClauseList

from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)
from apps.activities.domain import ActivityHistory
from apps.activities.domain.activity_full import ActivityItemHistoryFull
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema
from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.domain import (
    AnswerItemDataEncrypted,
    AppletCompletedEntities,
    CompletedEntity,
    IdentifiersQueryParams,
    RespondentAnswerData,
    UserAnswerItemData,
    Version,
)
from apps.answers.errors import AnswerNotFoundError
from apps.answers.filters import AppletActivityFilter, AppletSubmitDateFilter
from apps.applets.db.schemas import AppletHistorySchema
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

    target_subject_ids = FilterField(
        AnswerSchema.target_subject_id, Comparisons.IN
    )
    activity_history_ids = FilterField(
        AnswerSchema.activity_history_id, Comparisons.IN
    )
    from_date = FilterField(
        AnswerItemSchema.created_at, Comparisons.GREAT_OR_EQUAL
    )
    to_date = FilterField(
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
        self, applet_id: uuid.UUID, filters: AppletActivityFilter
    ) -> list[AnswerSchema]:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(
            func.date(AnswerSchema.created_at) == filters.created_date
        )
        if filters.respondent_id:
            query = query.where(
                AnswerSchema.respondent_id == filters.respondent_id
            )
        if filters.target_subject_id:
            query = query.where(
                AnswerSchema.target_subject_id == filters.target_subject_id
            )
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_respondents_submit_dates(
        self, applet_id: uuid.UUID, filters: AppletSubmitDateFilter
    ) -> list[datetime.date]:
        query: Query = select(func.date(AnswerSchema.created_at))
        query = query.where(
            func.date(AnswerSchema.created_at) >= filters.from_date
        )
        query = query.where(
            func.date(AnswerSchema.created_at) <= filters.to_date
        )
        query = query.where(AnswerSchema.applet_id == applet_id)
        if filters.respondent_id:
            query = query.where(
                AnswerSchema.respondent_id == filters.respondent_id
            )
        if filters.target_subject_id:
            query = query.where(
                AnswerSchema.target_subject_id == filters.target_subject_id
            )
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

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None = None
    ):
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
                self._exclude_assessment_val(
                    AnswerSchema.target_subject_id
                ).label("target_subject_id"),
                self._exclude_assessment_val(
                    AnswerSchema.source_subject_id
                ).label("source_subject_id"),
                self._exclude_assessment_val(AnswerSchema.relation).label(
                    "relation"
                ),
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
            )
            .select_from(AnswerSchema)
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
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

        coro_data, coro_count = self._execute(query), self._execute(
            query_count
        )

        res, res_count = await asyncio.gather(coro_data, coro_count)
        answers = res.all()

        total = res_count.scalars().one()

        return parse_obj_as(list[RespondentAnswerData], answers), total

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
        self,
        activity_hist_ids: Collection[str],
        filters: IdentifiersQueryParams,
    ) -> list[tuple[str, str, dict]]:
        query: Query = select(
            AnswerItemSchema.identifier,
            AnswerItemSchema.user_public_key,
            AnswerItemSchema.migrated_data,
        )
        query = query.distinct(AnswerItemSchema.identifier)
        query = query.where(
            AnswerItemSchema.identifier.isnot(None),
            AnswerSchema.activity_history_id.in_(activity_hist_ids),
        )
        if filters.target_subject_id:
            query = query.where(
                AnswerSchema.target_subject_id == filters.target_subject_id
            )
        if filters.respondent_id:
            query = query.where(
                AnswerSchema.respondent_id == filters.respondent_id
            )

        query = query.join(
            AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id
        )
        db_result = await self._execute(query)

        return db_result.all()  # noqa

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
        activity_id: Collection[str],
        respond_id: uuid.UUID,
    ) -> AnswerSchema | None:
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.activity_history_id.in_(activity_id))
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
        created_time = datetime.datetime.utcfromtimestamp(created_at)
        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.created_at == created_time)
        query = query.filter(
            AnswerSchema.activity_history_id.startswith(activity_id)
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_activities_which_has_answer(
        self,
        activity_hist_ids: list[str],
        respondent_id: uuid.UUID | None,
        subject_id: uuid.UUID | None,
    ) -> list[str]:
        activity_ids = set(
            map(lambda id_version: id_version.split("_")[0], activity_hist_ids)
        )
        query: Query = select(AnswerSchema.activity_history_id)
        query = query.where(
            or_(
                *(
                    AnswerSchema.activity_history_id.like(f"{item}_%")
                    for item in activity_ids
                )
            )
        )
        if respondent_id:
            query = query.where(AnswerSchema.respondent_id == respondent_id)
        if subject_id:
            query = query.where(AnswerSchema.target_subject_id == subject_id)
        query = query.distinct(AnswerSchema.activity_history_id)
        query = query.order_by(AnswerSchema.activity_history_id)
        db_result = await self._execute(query)
        results = []
        for activity_id in db_result.all():
            results.append(activity_id)
        return [row[0] for row in results]

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
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
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
                activities.append(
                    CompletedEntity(**row, id=row.activity_history_id)
                )

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
        applet_version_filter: BooleanClauseList = or_(
            *applet_version_filter_list
        )

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
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
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
            applet_activities_flows_map.setdefault(
                row.applet_id, {"activities": [], "flows": []}
            )
            if row.flow_history_id:
                applet_activities_flows_map[row.applet_id]["flows"].append(
                    CompletedEntity(**row, id=row.flow_history_id)
                )
            else:
                applet_activities_flows_map[row.applet_id][
                    "activities"
                ].append(CompletedEntity(**row, id=row.activity_history_id))

        result_list: list[AppletCompletedEntities] = list()
        for applet_id, version in applets_version_map.items():
            result_list.append(
                AppletCompletedEntities(
                    id=applet_id,
                    version=version,
                    activities=applet_activities_flows_map.get(
                        applet_id, {"activities": [], "flows": []}
                    )["activities"],
                    activity_flows=applet_activities_flows_map.get(
                        applet_id, {"activities": [], "flows": []}
                    )["flows"],
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
            .join(
                AnswerItemSchema, AnswerItemSchema.answer_id == AnswerSchema.id
            )
            .where(
                AnswerSchema.applet_id == applet_id,
                AnswerItemSchema.respondent_id == user_id,
            )
            .order_by(AnswerItemSchema.id)
        )
        query = paging(query, page, limit)

        db_result = await self._execute(query)

        return parse_obj_as(list[UserAnswerItemData], db_result.all())

    async def update_encrypted_fields(
        self, user_public_key: str, data: list[AnswerItemDataEncrypted]
    ):
        if data:
            vals = Values(
                column("id", UUID(as_uuid=True)),
                column("answer", Text),
                column("events", Text),
                column("identifier", Text),
                name="answer_data",
            ).data(
                [
                    (row.id, row.answer, row.events, row.identifier)
                    for row in data
                ]
            )
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
        query = query.where(
            ActivityFlowHistoriesSchema.id_version == answer_flow_id
        )
        db_result = await self._execute(query)
        db_result = db_result.first()
        flow_history_schema = (
            db_result[0] if db_result else None
        )  # type: ActivityFlowHistoriesSchema | None
        if not flow_history_schema:
            return False
        return flow_history_schema.is_single_report

    async def get_last_activity(
        self, respondent_ids: list[uuid.UUID], applet_id: uuid.UUID | None
    ) -> dict[uuid.UUID, datetime.datetime]:
        query: Query = (
            select(
                AnswerSchema.respondent_id, func.max(AnswerSchema.created_at)
            )
            .group_by(AnswerSchema.respondent_id)
            .where(AnswerSchema.respondent_id.in_(respondent_ids))
        )
        if applet_id:
            query = query.where(AnswerSchema.applet_id == applet_id)
        result = await self._execute(query)
        return {t[0]: t[1] for t in result.all()}
