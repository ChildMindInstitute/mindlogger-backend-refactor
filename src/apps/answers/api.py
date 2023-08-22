import base64
import datetime
import uuid

from fastapi import Body, Depends, Query
from fastapi.responses import Response as FastApiResponse
from pydantic import parse_obj_as

from apps.activities.services import ActivityHistoryService
from apps.answers.domain import (
    ActivityAnswerPublic,
    AnswerExport,
    AnswerNote,
    AnswerNoteDetailPublic,
    AnswerReviewPublic,
    AnswersCheck,
    AppletActivityAnswerPublic,
    AppletAnswerCreate,
    AssessmentAnswerCreate,
    AssessmentAnswerPublic,
    IdentifierPublic,
    PublicAnswerDates,
    PublicAnswerExport,
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
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.shared.query_params import (
    BaseQueryParams,
    QueryParams,
    parse_query_params,
)
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def create_answer(
    user: User = Depends(get_current_user),
    schema: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_answer_create_access(
            schema.applet_id
        )
        await AnswerService(session, user.id).create_answer(schema)
    return


async def create_anonymous_answer(
    schema: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        anonymous_respondent = await UsersCRUD(
            session
        ).get_anonymous_respondent()
        await AnswerService(
            session, anonymous_respondent.id  # type: ignore
        ).create_answer(schema)
    return


async def review_activity_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(
        parse_query_params(AppletActivityFilter)
    ),
) -> ResponseMulti[PublicReviewActivity]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        activities = await AnswerService(
            session, user.id
        ).get_review_activities(applet_id, **query_params.filters)
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
) -> ResponseMulti[PublicSummaryActivity]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        activities = await AnswerService(
            session, user.id
        ).get_summary_activities(
            applet_id, query_params.filters.get("respondent_id")
        )
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
) -> ResponseMulti[AppletActivityAnswerPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        answers = await AnswerService(session, user.id).get_activity_answers(
            applet_id, activity_id, query_params
        )
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
) -> FastApiResponse:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        report = await AnswerService(
            session, user.id
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
) -> Response[PublicAnswerDates]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        dates = await AnswerService(session, user.id).get_applet_submit_dates(
            applet_id, **query_params.filters
        )
    return Response(result=PublicAnswerDates(dates=list(sorted(set(dates)))))


async def applet_activity_answer_retrieve(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[ActivityAnswerPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        answer = await AnswerService(session, user.id).get_by_id(
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
) -> ResponseMulti[AnswerReviewPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        reviews = await AnswerService(
            session, user.id
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
) -> Response[AssessmentAnswerPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        answer = await AnswerService(
            session, user.id
        ).get_assessment_by_answer_id(applet_id, answer_id)
    return Response(
        result=AssessmentAnswerPublic.from_orm(answer),
    )


async def applet_activity_identifiers_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[IdentifierPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        identifiers = await AnswerService(
            session, user.id
        ).get_activity_identifiers(activity_id)
    return ResponseMulti(result=identifiers, count=len(identifiers))


async def applet_activity_versions_retrieve(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[VersionPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        versions = await AnswerService(session, user.id).get_activity_versions(
            activity_id
        )
    return ResponseMulti(
        result=parse_obj_as(list[VersionPublic], versions), count=len(versions)
    )


async def applet_activity_assessment_create(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    schema: AssessmentAnswerCreate = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        await AnswerService(session, user.id).create_assessment_answer(
            applet_id, answer_id, schema
        )
    return


async def note_add(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
    schema: AnswerNote = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
        await AnswerService(session, user.id).add_note(
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
) -> ResponseMulti[AnswerNoteDetailPublic]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
        notes = await AnswerService(session, user.id).get_note_list(
            applet_id, answer_id, activity_id, query_params
        )
        count = await AnswerService(session, user.id).get_notes_count(
            answer_id, activity_id
        )
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
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
        await AnswerService(session, user.id).edit_note(
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
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_note_crud_access(
            applet_id
        )
        await AnswerService(session, user.id).delete_note(
            applet_id, answer_id, activity_id, note_id
        )
    return


async def applet_answers_export(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AnswerExportFilters)
    ),
    session=Depends(get_session),
):
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answers_export_access(
        applet_id
    )
    data: AnswerExport = await AnswerService(session, user.id).get_export_data(
        applet_id, query_params
    )
    for answer in data.answers:
        if answer.is_manager:
            answer.respondent_secret_id = (
                f"[admin account]({answer.respondent_email})"
            )

    if not data.activities:
        applet = await AppletService(session, user.id).get(applet_id)
        activities = await ActivityHistoryService(
            session, applet.id, applet.version
        ).get_full()
        data.activities = activities

    return Response(result=PublicAnswerExport.from_orm(data))


async def applet_completed_entities(
    applet_id: uuid.UUID,
    version: str,
    from_date: datetime.date = Query(..., alias="fromDate"),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_answer_create_access(
        applet_id
    )
    data = await AnswerService(session, user.id).get_completed_answers_data(
        applet_id, version, from_date
    )

    return Response(result=data)


async def answers_existence_check(
    schema: AnswersCheck = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Provides the information if the anwer is existed in the database.
    HTTP 200 OK means that yes.
    HTTP 404 NOT FOUND means that it is not.
    """
    await AppletService(session, user.id).exist_by_id(schema.applet_id)
    await CheckAccessService(session, user.id).check_answer_check_access(
        schema.applet_id
    )
    if (
        await AnswerService(session, user.id).is_answers_uploaded(
            schema.applet_id, schema.activity_id, schema.created_at
        )
    ) is False:
        raise NotFoundError
