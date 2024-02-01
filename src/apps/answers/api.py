import asyncio
import base64
import datetime
import uuid

from fastapi import Body, Depends, Query
from fastapi.responses import Response as FastApiResponse
from pydantic import parse_obj_as

from apps.activities.services import ActivityHistoryService
from apps.answers.deps.preprocess_arbitrary import (
    get_answer_session,
    get_arbitraries_map,
)
from apps.answers.domain import (
    ActivityAnswerPublic,
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
    IdentifierPublic,
    IdentifiersQueryParams,
    PublicAnswerDates,
    PublicAnswerExport,
    PublicAnswerExportResponse,
    PublicReviewActivity,
    PublicSummaryActivity,
    VersionPublic,
)
from apps.answers.filters import (
    AnswerExportFilters,
    AppletActivityAnswerFilter,
    AppletActivityFilter,
    AppletSubmitDateFilter,
    SummaryActivityFilter,
)
from apps.answers.service import AnswerService
from apps.applets.crud import AppletsCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.errors import InvalidVersionError, NotValidAppletHistory
from apps.applets.service import AppletHistoryService, AppletService
from apps.authentication.deps import get_current_user
from apps.shared.deps import get_i18n
from apps.shared.domain import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.shared.locale import I18N
from apps.shared.query_params import (
    BaseQueryParams,
    QueryParams,
    parse_query_params,
)
from apps.subjects.services import SubjectsService
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager
from infrastructure.database.deps import get_session


async def create_answer(
    user: User = Depends(get_current_user),
    schema: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> None:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_answer_create_access(
            schema.applet_id
        )
        try:
            await AppletHistoryService(
                session, schema.applet_id, schema.version
            ).get()
        except NotValidAppletHistory:
            raise InvalidVersionError()
        service = AnswerService(session, user.id, answer_session)
        async with atomic(answer_session):
            answer = await service.create_answer(schema)
        await service.create_report_from_answer(answer)


async def create_anonymous_answer(
    schema: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> None:
    async with atomic(session):
        anonymous_respondent = await UsersCRUD(
            session
        ).get_anonymous_respondent()
        assert anonymous_respondent

        service = AnswerService(
            session, anonymous_respondent.id, answer_session
        )
        async with atomic(answer_session):
            answer = await service.create_answer(schema)
        await service.create_report_from_answer(answer)
    return


async def review_activity_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(
        parse_query_params(AppletActivityFilter)
    ),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicReviewActivity]:
    filters = AppletActivityFilter(**query_params.filters)
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_access(
        applet_id, **filters.dict()
    )
    activities = await AnswerService(
        session, user.id, answer_session
    ).get_review_activities(applet_id, filters)

    return ResponseMulti(
        result=[
            PublicReviewActivity.from_orm(activity) for activity in activities
        ],
        count=len(activities),
    )


async def summary_activity_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(
        parse_query_params(SummaryActivityFilter)
    ),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[PublicSummaryActivity]:
    filters = SummaryActivityFilter(**query_params.filters)
    await AppletService(session, user.id).exist_by_id(applet_id)
    if filters.respondent_id and not filters.target_subject_id:
        target_subject = await (
            SubjectsService(session, user.id).get_by_user_and_applet(
                filters.respondent_id, applet_id
            )
        )
        if not target_subject:
            raise NotFoundError()
        target_subject_id = target_subject.id
    else:
        target_subject_id = filters.target_subject_id
    await CheckAccessService(session, user.id).check_subject_answer_access(
        applet_id, target_subject_id
    )
    activities = await AnswerService(
        session, user.id, answer_session
    ).get_summary_activities(applet_id, filters)
    return ResponseMulti(
        result=parse_obj_as(list[PublicSummaryActivity], activities),
        count=len(activities),
    )


async def applet_activity_answers_list(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(
        parse_query_params(AppletActivityAnswerFilter)
    ),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[AppletActivityAnswerPublic]:
    filters = AppletActivityAnswerFilter(**query_params.filters)
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_access(
        applet_id, **filters.dict()
    )
    answers = await AnswerService(
        session, user.id, answer_session
    ).get_activity_answers(applet_id, activity_id, filters)
    return ResponseMulti(
        result=parse_obj_as(list[AppletActivityAnswerPublic], answers),
        count=len(answers),
    )


async def summary_latest_report_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> FastApiResponse:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(
        applet_id
    )
    report = await AnswerService(
        session, user.id, answer_session
    ).get_summary_latest_report(applet_id, activity_id, respondent_id)
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
    query_params: QueryParams = Depends(
        parse_query_params(AppletSubmitDateFilter)
    ),
    answer_session=Depends(get_answer_session),
) -> Response[PublicAnswerDates]:
    filters = AppletSubmitDateFilter(**query_params.filters)
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_access(
        applet_id, **filters.dict()
    )
    dates = await AnswerService(
        session, user.id, answer_session
    ).get_applet_submit_dates(
        applet_id, AppletSubmitDateFilter(**query_params.filters)
    )
    return Response(result=PublicAnswerDates(dates=list(sorted(set(dates)))))


async def applet_activity_answer_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[ActivityAnswerPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(
        applet_id
    )
    answer = await AnswerService(session, user.id, answer_session).get_by_id(
        applet_id, answer_id, activity_id
    )
    return Response(
        result=ActivityAnswerPublic.from_orm(answer),
    )


async def applet_answer_reviews_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[AnswerReviewPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(
        applet_id
    )
    reviews = await AnswerService(
        session, user.id, answer_session
    ).get_reviews_by_answer_id(applet_id, answer_id)
    return ResponseMulti(
        result=[AnswerReviewPublic.from_orm(review) for review in reviews],
        count=len(reviews),
    )


async def applet_activity_assessment_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AssessmentAnswerPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(
        applet_id
    )
    answer = await AnswerService(
        session, user.id, answer_session
    ).get_assessment_by_answer_id(applet_id, answer_id)
    return Response(
        result=AssessmentAnswerPublic.from_orm(answer),
    )


async def applet_activity_identifiers_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    query_params: QueryParams = Depends(
        parse_query_params(IdentifiersQueryParams)
    ),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[IdentifierPublic]:
    filters = IdentifiersQueryParams(**query_params.filters)
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_access(
        applet_id, **filters.dict()
    )
    identifiers = await AnswerService(
        session, user.id, answer_session
    ).get_activity_identifiers(activity_id, filters)
    return ResponseMulti(result=identifiers, count=len(identifiers))


async def applet_activity_versions_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[VersionPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_review_access(
        applet_id
    )
    versions = await AnswerService(
        session, user.id, arbitrary_session=answer_session
    ).get_activity_versions(activity_id)
    return ResponseMulti(
        result=parse_obj_as(list[VersionPublic], versions), count=len(versions)
    )


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
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        async with atomic(answer_session):
            await AnswerService(
                session, user.id, answer_session
            ).create_assessment_answer(applet_id, answer_id, schema)


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
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
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
    await CheckAccessService(session, user.id).check_note_crud_access(
        applet_id
    )
    notes = await AnswerService(
        session, user.id, answer_session
    ).get_note_list(applet_id, answer_id, activity_id, query_params)
    count = await AnswerService(
        session, user.id, answer_session
    ).get_notes_count(answer_id, activity_id)
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
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
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
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
        async with atomic(answer_session):
            await AnswerService(session, user.id, answer_session).delete_note(
                applet_id, answer_id, activity_id, note_id
            )
    return


async def applet_answers_export(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AnswerExportFilters)
    ),
    activities_last_version: bool = Query(
        False, alias="activitiesLastVersion"
    ),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
    i18n: I18N = Depends(get_i18n),
):
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answers_export_access(
        applet_id
    )
    data: AnswerExport = await AnswerService(
        session, user.id, answer_session
    ).get_export_data(applet_id, query_params, activities_last_version)
    total_answers = data.total_answers
    for answer in data.answers:
        if answer.is_manager:
            answer.respondent_secret_id = (
                f"[admin account] ({answer.respondent_email})"
            )

    if activities_last_version:
        applet = await AppletService(session, user.id).get(applet_id)
        activities = await ActivityHistoryService(
            session, applet.id, applet.version
        ).get_full()
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
):
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_create_access(
        applet_id
    )
    data = await AnswerService(
        session, user.id, answer_session
    ).get_completed_answers_data(applet_id, version, from_date)

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
    applets: list[AppletSchema] = await AppletsCRUD(
        session
    ).get_applets_by_roles(
        user_id=user.id,
        roles=[Role.RESPONDENT],
        query_params=query_params,
        exclude_without_encryption=True,
    )

    applets_version_map: dict[uuid.UUID, str] = dict()
    for applet in applets:
        applets_version_map[applet.id] = applet.version
    applet_ids: list[uuid.UUID] = list(applets_version_map.keys())

    arb_uri_applet_ids_map: dict[
        str | None, list[uuid.UUID]
    ] = await get_arbitraries_map(applet_ids, session)

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
            data = AnswerService(
                session, user_id=user.id
            ).get_completed_answers_data_list(
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
    await CheckAccessService(session, user.id).check_answer_check_access(
        schema.applet_id
    )
    is_exist = await AnswerService(
        session, user.id, answer_session
    ).is_answers_uploaded(
        schema.applet_id, schema.activity_id, schema.created_at
    )

    return Response[AnswerExistenceResponse](
        result=AnswerExistenceResponse(exists=is_exist)
    )
