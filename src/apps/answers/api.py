import asyncio
import base64
import datetime
import uuid

from fastapi import Body, Depends, Query
from fastapi.responses import Response as FastApiResponse
from pydantic import parse_obj_as

from apps.activities.services import ActivityHistoryService
from apps.activity_flows.service.flow import FlowService
from apps.answers.deps.preprocess_arbitrary import get_answer_session, get_arbitraries_map
from apps.answers.domain import (
    ActivitySubmissionResponse,
    AnswerExistenceResponse,
    AnswerExport,
    AnswerNote,
    AnswerNoteDetailPublic,
    AnswerReviewPublic,
    AnswersCheck,
    AppletActivityAnswerPublic,
    AppletAnswerCreate,
    AppletCompletedEntities,
    AssessmentAnswerCreate,
    AssessmentAnswerPublic,
    FlowSubmissionResponse,
    Identifier,
    IdentifiersQueryParams,
    PublicAnswerDates,
    PublicAnswerExport,
    PublicAnswerExportResponse,
    PublicFlowSubmissionsResponse,
    PublicReviewActivity,
    PublicReviewFlow,
    PublicSummaryActivity,
    PublicSummaryActivityFlow,
    ReviewsCount,
)
from apps.answers.filters import (
    AnswerExportFilters,
    AppletSubmissionsFilter,
    AppletSubmitDateFilter,
    ReviewAppletItemFilter,
    SummaryActivityFilter,
)
from apps.answers.service import AnswerService
from apps.applets.crud import AppletsCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain.applet_history import VersionPublic
from apps.applets.errors import InvalidVersionError, NotValidAppletHistory
from apps.applets.service import AppletHistoryService, AppletService
from apps.authentication.deps import get_current_user
from apps.shared.deps import get_i18n
from apps.shared.domain import Response, ResponseMulti
from apps.shared.exception import AccessDeniedError, NotFoundError
from apps.shared.locale import I18N
from apps.shared.query_params import BaseQueryParams, QueryParams, parse_query_params
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager
from infrastructure.database.deps import get_session
from infrastructure.http import get_tz_utc_offset


async def create_answer(
    user: User = Depends(get_current_user),
    schema: AppletAnswerCreate = Body(...),
    tz_offset: int | None = Depends(get_tz_utc_offset()),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> None:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_answer_create_access(schema.applet_id)
        try:
            await AppletHistoryService(session, schema.applet_id, schema.version).get()
        except NotValidAppletHistory:
            raise InvalidVersionError()
        service = AnswerService(session, user.id, answer_session)
        if tz_offset is not None and schema.answer.tz_offset is None:
            schema.answer.tz_offset = tz_offset // 60  # value in minutes
        async with atomic(answer_session):
            answer = await service.create_answer(schema)
        await service.create_report_from_answer(answer)


async def create_anonymous_answer(
    schema: AppletAnswerCreate = Body(...),
    tz_offset: int | None = Depends(get_tz_utc_offset()),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> None:
    async with atomic(session):
        anonymous_respondent = await UsersCRUD(session).get_anonymous_respondent()
        assert anonymous_respondent

        service = AnswerService(session, anonymous_respondent.id, answer_session)
        if tz_offset is not None and schema.answer.tz_offset is None:
            schema.answer.tz_offset = tz_offset // 60  # value in minutes
        async with atomic(answer_session):
            answer = await service.create_answer(schema)
        await service.create_report_from_answer(answer)
    return


async def review_activity_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(ReviewAppletItemFilter)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicReviewActivity]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    activities = await AnswerService(session, user.id, answer_session).get_review_activities(
        applet_id, **query_params.filters
    )

    return ResponseMulti(
        result=[PublicReviewActivity.from_orm(activity) for activity in activities],
        count=len(activities),
    )


async def review_flow_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(ReviewAppletItemFilter)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicReviewFlow]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    flows = await AnswerService(session, user.id, answer_session).get_review_flows(applet_id, **query_params.filters)

    return ResponseMulti(
        result=parse_obj_as(list[PublicReviewFlow], flows),
        count=len(flows),
    )


async def summary_activity_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(SummaryActivityFilter)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicSummaryActivity]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    respondent_id = query_params.filters.get("respondent_id")
    await CheckAccessService(session, user.id).check_summary_access(applet_id, respondent_id)
    activities = await AnswerService(session, user.id, answer_session).get_summary_activities(
        applet_id, query_params.filters.get("respondent_id")
    )
    return ResponseMulti(
        result=parse_obj_as(list[PublicSummaryActivity], activities),
        count=len(activities),
    )


async def summary_activity_flow_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(SummaryActivityFilter)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicSummaryActivityFlow]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    respondent_id = query_params.filters.get("respondent_id")  # todo: Change to target_subject_id
    await CheckAccessService(session, user.id).check_summary_access(applet_id, respondent_id)
    activities = await AnswerService(session, user.id, answer_session).get_summary_activity_flows(
        applet_id, respondent_id
    )
    return ResponseMulti(
        result=parse_obj_as(list[PublicSummaryActivityFlow], activities),
        count=len(activities),
    )


async def applet_activity_answers_list(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(AppletSubmissionsFilter)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[AppletActivityAnswerPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    service = AnswerService(session, user.id, answer_session)
    answers = await service.get_activity_answers(applet_id, activity_id, query_params)

    answers_ids = [answer.answer_id for answer in answers if answer.answer_id is not None]
    answer_reviews = await service.get_assessments_count(answers_ids)
    result = []
    for answer in answers:
        review_count = answer_reviews.get(answer.answer_id, ReviewsCount())
        result.append(parse_obj_as(AppletActivityAnswerPublic, {**answer.dict(), "review_count": review_count}))
    return ResponseMulti(result=result, count=len(answers))


async def applet_flow_submissions_list(
    applet_id: uuid.UUID,
    flow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AppletSubmissionsFilter)),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> PublicFlowSubmissionsResponse:
    await AppletService(session, user.id).exist_by_id(applet_id)
    flow = await FlowService(session=session).get_by_id(flow_id)
    if not flow or flow.applet_id != applet_id:
        raise NotFoundError("Flow not found")
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)

    submissions, total = await AnswerService(session, user.id, answer_session).get_flow_submissions(
        flow_id, query_params
    )

    return PublicFlowSubmissionsResponse(result=submissions, count=total)


async def summary_latest_report_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> FastApiResponse:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    report = await AnswerService(session, user.id, answer_session).get_summary_latest_report(
        applet_id, activity_id, respondent_id
    )
    if report:
        return FastApiResponse(
            base64.b64decode(report.pdf.encode()),
            headers={
                "Content-Disposition": f'attachment; filename="{report.email.attachment}.pdf"'  # noqa
            },
        )
    return FastApiResponse()


async def applet_submit_date_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(AppletSubmitDateFilter)),
    answer_session=Depends(get_answer_session),
) -> Response[PublicAnswerDates]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    dates = await AnswerService(session, user.id, answer_session).get_applet_submit_dates(
        applet_id, **query_params.filters
    )
    return Response(result=PublicAnswerDates(dates=list(sorted(set(dates)))))


async def applet_activity_answer_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    answer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[ActivitySubmissionResponse]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    submission = await AnswerService(session, user.id, answer_session).get_activity_answer(
        applet_id, activity_id, answer_id
    )
    result = ActivitySubmissionResponse.from_orm(submission)
    return Response(result=result)


async def applet_flow_answer_retrieve(
    applet_id: uuid.UUID,
    flow_id: uuid.UUID,
    submit_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[FlowSubmissionResponse]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    submission = await AnswerService(session, user.id, answer_session).get_flow_submission(
        applet_id, flow_id, submit_id
    )
    result = FlowSubmissionResponse.from_orm(submission)
    return Response(result=result)


async def applet_answer_reviews_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[AnswerReviewPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    reviews = await AnswerService(session, user.id, answer_session).get_reviews_by_answer_id(applet_id, answer_id)
    return ResponseMulti(
        result=[AnswerReviewPublic.from_orm(review) for review in reviews],
        count=len(reviews),
    )


async def applet_answer_assessment_delete(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    assessment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> None:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    service = AnswerService(session=session, user_id=user.id, arbitrary_session=answer_session)
    assessment = await service.get_answer_assessment_by_id(assessment_id, answer_id)
    if not assessment:
        raise NotFoundError
    elif assessment.respondent_id != user.id:
        raise AccessDeniedError
    async with atomic(session):
        async with atomic(answer_session):
            await service.delete_assessment(assessment_id)


async def applet_activity_assessment_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AssessmentAnswerPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    answer = await AnswerService(session, user.id, answer_session).get_assessment_by_answer_id(applet_id, answer_id)
    return Response(
        result=AssessmentAnswerPublic.from_orm(answer),
    )


async def applet_activity_identifiers_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    query_params: QueryParams = Depends(parse_query_params(IdentifiersQueryParams)),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[Identifier]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    identifiers = await AnswerService(session, user.id, answer_session).get_activity_identifiers(
        activity_id, query_params.filters["respondent_id"]
    )
    return ResponseMulti(result=identifiers, count=len(identifiers))


async def applet_flow_identifiers_retrieve(
    applet_id: uuid.UUID,
    flow_id: uuid.UUID,
    query_params: QueryParams = Depends(parse_query_params(IdentifiersQueryParams)),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[Identifier]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    flow = await FlowService(session=session).get_by_id(flow_id)
    if not flow or flow.applet_id != applet_id:
        raise NotFoundError("Flow not found")
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)

    identifiers = await AnswerService(session, user.id, answer_session).get_flow_identifiers(
        flow_id, query_params.filters["respondent_id"]
    )
    return ResponseMulti(result=identifiers, count=len(identifiers))


async def applet_activity_versions_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[VersionPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
    versions = await AnswerService(session, user.id, arbitrary_session=answer_session).get_activity_versions(
        activity_id
    )
    return ResponseMulti(result=parse_obj_as(list[VersionPublic], versions), count=len(versions))


async def applet_activity_assessment_create(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    schema: AssessmentAnswerCreate = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(applet_id)
        async with atomic(answer_session):
            await AnswerService(session, user.id, answer_session).create_assessment_answer(applet_id, answer_id, schema)


async def note_add(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    schema: AnswerNote = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(applet_id)
        async with atomic(answer_session):
            await AnswerService(session, user.id, answer_session).add_note(
                applet_id, answer_id, activity_id, schema.note
            )
    return


async def note_list(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(BaseQueryParams)),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[AnswerNoteDetailPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_note_crud_access(applet_id)
    notes = await AnswerService(session, user.id, answer_session).get_note_list(
        applet_id, answer_id, activity_id, query_params
    )
    count = await AnswerService(session, user.id, answer_session).get_notes_count(answer_id, activity_id)
    return ResponseMulti(
        result=[AnswerNoteDetailPublic.from_orm(note) for note in notes],
        count=count,
    )


async def note_edit(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    note_id: uuid.UUID,
    schema: AnswerNote = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(applet_id)
        async with atomic(answer_session):
            await AnswerService(session, user.id, answer_session).edit_note(
                applet_id, answer_id, activity_id, note_id, schema.note
            )
    return


async def note_delete(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    note_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(applet_id)
        async with atomic(answer_session):
            await AnswerService(session, user.id, answer_session).delete_note(
                applet_id, answer_id, activity_id, note_id
            )
    return


async def applet_answers_export(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AnswerExportFilters)),
    activities_last_version: bool = Query(False, alias="activitiesLastVersion"),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
    i18n: I18N = Depends(get_i18n),
) -> PublicAnswerExportResponse:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answers_export_access(applet_id)
    data: AnswerExport = await AnswerService(session, user.id, answer_session).get_export_data(
        applet_id, query_params, activities_last_version
    )
    total_answers = data.total_answers
    for answer in data.answers:
        if answer.is_manager:
            answer.respondent_secret_id = f"[admin account] ({answer.respondent_secret_id})"

    if activities_last_version:
        applet = await AppletService(session, user.id).get(applet_id)
        activities = await ActivityHistoryService(session, applet.id, applet.version).get_full()
        data.activities = activities
    return PublicAnswerExportResponse(
        result=PublicAnswerExport.from_orm(data).translate(i18n),
        count=total_answers,
    )


async def applet_completed_entities(
    applet_id: uuid.UUID,
    version: str,
    from_date: datetime.date = Query(..., alias="fromDate"),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AppletCompletedEntities]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_create_access(applet_id)
    data = await AnswerService(session, user.id, answer_session).get_completed_answers_data(
        applet_id, version, from_date
    )

    return Response(result=data)


async def _get_arbitrary_answer(
    session,
    from_date: datetime.date,
    arb_uri: str,
    applets_version_map: dict[uuid.UUID, str],
    user_id: uuid.UUID | None = None,
) -> list[AppletCompletedEntities]:
    arb_session_maker = session_manager.get_session(arb_uri)
    async with arb_session_maker() as arb_session:
        data = await AnswerService(
            session,
            user_id=user_id,
            arbitrary_session=arb_session,
        ).get_completed_answers_data_list(applets_version_map, from_date)

    return data


async def applets_completed_entities(
    from_date: datetime.date = Query(..., alias="fromDate"),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[AppletCompletedEntities]:
    # applets for this endpoint must be equal to
    # applets from /applets?roles=respondent endpoint
    query_params: QueryParams = QueryParams(
        filters={"roles": Role.RESPONDENT, "flat_list": False},
        limit=10000,
    )
    applets: list[AppletSchema] = await AppletsCRUD(session).get_applets_by_roles(
        user_id=user.id,
        roles=[Role.RESPONDENT],
        query_params=query_params,
        exclude_without_encryption=True,
    )

    applets_version_map: dict[uuid.UUID, str] = dict()
    for applet in applets:
        applets_version_map[applet.id] = applet.version
    applet_ids: list[uuid.UUID] = list(applets_version_map.keys())

    arb_uri_applet_ids_map: dict[str | None, list[uuid.UUID]] = await get_arbitraries_map(applet_ids, session)

    data_future_list = []
    for arb_uri, arb_applet_ids in arb_uri_applet_ids_map.items():
        applets_version_arb_map: dict[uuid.UUID, str] = dict()
        for applet_id in arb_applet_ids:
            applets_version_arb_map[applet_id] = applets_version_map[applet_id]

        if arb_uri:
            data = _get_arbitrary_answer(
                session,
                from_date,
                arb_uri,
                applets_version_arb_map,
                user_id=user.id,
            )
        else:
            data = AnswerService(session, user_id=user.id).get_completed_answers_data_list(
                applets_version_arb_map, from_date
            )
        data_future_list.append(data)

    entities_lists = await asyncio.gather(*data_future_list)
    entities = []

    for entities_list in entities_lists:
        if entities_list:
            entities += entities_list

    return ResponseMulti(result=entities, count=len(entities))


async def answers_existence_check(
    schema: AnswersCheck = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AnswerExistenceResponse]:
    """Provides information whether the answer exists"""
    await AppletService(session, user.id).exist_by_id(schema.applet_id)
    await CheckAccessService(session, user.id).check_answer_check_access(schema.applet_id)
    is_exist = await AnswerService(session, user.id, answer_session).is_answers_uploaded(
        schema.applet_id, schema.activity_id, schema.created_at
    )

    return Response[AnswerExistenceResponse](result=AnswerExistenceResponse(exists=is_exist))
