import uuid

from fastapi import Body, Depends

from apps.answers.domain import (
    ActivityAnswerPublic,
    AnswerExport,
    AnswerNote,
    AnswerNoteDetailPublic,
    AnswerReviewPublic,
    AppletAnswerCreate,
    AssessmentAnswerCreate,
    AssessmentAnswerPublic,
    PublicAnswerDates,
    PublicAnsweredAppletActivity,
    PublicAnswerExport,
)
from apps.answers.filters import (
    AnswerExportFilters,
    AppletActivityFilter,
    AppletSubmitDateFilter,
)
from apps.answers.service import AnswerService
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import (
    BaseQueryParams,
    QueryParams,
    parse_query_params,
)
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
        await AnswerService(session).create_answer(schema)
    return


async def applet_activities_list(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(
        parse_query_params(AppletActivityFilter)
    ),
) -> ResponseMulti[PublicAnsweredAppletActivity]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_answer_review_access(
            applet_id
        )
        activities = await AnswerService(session, user.id).applet_activities(
            applet_id, **query_params.filters
        )
    return ResponseMulti(
        result=[
            PublicAnsweredAppletActivity.from_orm(activity)
            for activity in activities
        ],
        count=len(activities),
    )


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
    activity_id: uuid.UUID,
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


async def applet_activity_assessment_create(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
    activity_id: uuid.UUID,
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
            applet_id, answer_id, note_id, schema.note
        )
    return


async def note_delete(
    applet_id: uuid.UUID,
    answer_id: uuid.UUID,
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
            applet_id, answer_id, note_id
        )
    return


async def applet_answers_export(
    applet_id: uuid.UUID,
    query_params: QueryParams = Depends(
        parse_query_params(AnswerExportFilters)
    ),
    user: User = Depends(get_current_user),
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

    return Response(result=PublicAnswerExport.from_orm(data))
