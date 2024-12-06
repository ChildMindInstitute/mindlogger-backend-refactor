import asyncio
import uuid

from fastapi import Depends

from apps.activities.crud import ActivitiesCRUD
from apps.activities.domain.activity import (
    ActivitiesMetadata,
    ActivityLanguageWithItemsMobileDetailPublic,
    ActivityOrFlowWithAssignmentsPublic,
    ActivitySingleLanguageWithItemsDetailPublic,
    ActivitySubjectMetadata,
    ActivityWithAssignmentDetailsPublic,
)
from apps.activities.filters import AppletActivityFilter
from apps.activities.services.activity import ActivityItemService, ActivityService
from apps.activity_assignments.service import ActivityAssignmentService
from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.domain.flow import FlowWithAssignmentDetailsPublic
from apps.activity_flows.service.flow import FlowService
from apps.answers.deps.preprocess_arbitrary import get_answer_session
from apps.answers.service import AnswerService
from apps.applets.domain.applet import (
    ActivitiesAndFlowsWithAssignmentDetailsPublic,
    AppletActivitiesAndFlowsDetailsPublic,
    AppletActivitiesDetailsPublic,
    AppletSingleLanguageDetailMobilePublic,
)
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session
from infrastructure.http import get_language


async def activity_retrieve(
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitySingleLanguageWithItemsDetailPublic]:
    async with atomic(session):
        schema = await ActivitiesCRUD(session).get_by_id(activity_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(schema.applet_id)
        activity = await ActivityService(session, user.id).get_single_language_by_id(activity_id, language)
    result = ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity)
    return Response(result=result)


async def public_activity_retrieve(
    id_: uuid.UUID,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitySingleLanguageWithItemsDetailPublic]:
    async with atomic(session):
        activity = await ActivityService(
            session, uuid.UUID("00000000-0000-0000-0000-000000000000")
        ).get_public_single_language_by_id(id_, language)

    return Response(result=ActivitySingleLanguageWithItemsDetailPublic.from_orm(activity))


async def applet_activities(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AppletActivityFilter)),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AppletActivitiesDetailsPublic]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

        filters = AppletActivityFilter(**query_params.filters)

        applet_future = service.get_single_language_by_id(applet_id, language)
        subject_future = SubjectsService(session, user.id).get_by_user_and_applet(user.id, applet_id)
        activities_future = ActivityService(session, user.id).get_single_language_with_items_by_applet_id(
            applet_id, language
        )

        applet, subject, activities = await asyncio.gather(
            applet_future,
            subject_future,
            activities_future,
        )
        applet_detail = AppletSingleLanguageDetailMobilePublic.from_orm(applet)
        respondent_meta = SubjectsService.to_respondent_meta(subject)

        if filters.has_submitted or filters.has_score:
            activities = await __filter_activities(
                activities, applet_id, user.id, filters, language, session, answer_session
            )

    result = AppletActivitiesDetailsPublic(
        activities_details=activities,
        applet_detail=applet_detail,
        respondent_meta=respondent_meta,
    )
    return Response(result=result)


async def applet_activities_for_subject(
    applet_id: uuid.UUID,
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[ActivitiesAndFlowsWithAssignmentDetailsPublic]:
    async with atomic(session):
        applet_service = AppletService(session, user.id)
        await applet_service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_respondent_list_access(applet_id)

        # Ensure reviewers can access the subject
        await CheckAccessService(session, user.id).check_subject_subject_access(applet_id, subject_id)

        activities_future = ActivityService(session, user.id).get_single_language_with_items_by_applet_id(
            applet_id, language
        )
        flows_future = FlowService(session).get_single_language_by_applet_id(applet_id, language)

        query_params = QueryParams(filters={"respondent_subject_id": subject_id, "target_subject_id": subject_id})
        assignments_future = ActivityAssignmentService(session).get_all_with_subject_entities(applet_id, query_params)

        activities, flows, assignments = await asyncio.gather(activities_future, flows_future, assignments_future)
        result = ActivitiesAndFlowsWithAssignmentDetailsPublic(
            activities=[],
            activity_flows=[],
        )

        for activity in activities:
            activity_with_assignment = ActivityWithAssignmentDetailsPublic(
                **activity.dict(exclude={"report_included_activity_name", "report_included_item_name"})
            )
            activity_with_assignment.assignments = [
                assignment for assignment in assignments if assignment.activity_id == activity.id
            ]

            if activity_with_assignment.auto_assign is True or len(activity_with_assignment.assignments) > 0:
                result.activities.append(activity_with_assignment)

        for flow in flows:
            flow_with_assignment = FlowWithAssignmentDetailsPublic(
                **flow.dict(exclude={"created_at", "report_included_activity_name", "report_included_item_name"})
            )
            flow_with_assignment.assignments = [
                assignment for assignment in assignments if assignment.activity_flow_id == flow.id
            ]

            if flow_with_assignment.auto_assign is True or len(flow_with_assignment.assignments) > 0:
                result.activity_flows.append(flow_with_assignment)

        return Response(result=result)


async def applet_activities_for_target_subject(
    applet_id: uuid.UUID,
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[ActivityOrFlowWithAssignmentsPublic]:
    applet_service = AppletService(session, user.id)
    await applet_service.exist_by_id(applet_id)

    subject = await SubjectsService(session, user.id).exist_by_id(subject_id)
    is_limited_respondent = subject.user_id is None

    # Restrict the endpoint access to owners, managers, coordinators, and assigned reviewers
    await CheckAccessService(session, user.id).check_subject_subject_access(applet_id, subject_id)

    assignments = await ActivityAssignmentService(session).get_all_with_subject_entities(
        applet_id, QueryParams(filters={"target_subject_id": subject_id})
    )

    # Only one of these IDs will be `None` at a time, so the resulting type will be a list of UUIDs
    activity_and_flow_ids_from_assignments: list[uuid.UUID] = [
        assignment.activity_id or assignment.activity_flow_id  # type: ignore
        for assignment in assignments
    ]

    activity_and_flow_ids_from_submissions = await AnswerService(
        session, user.id, answer_session
    ).get_activity_and_flow_ids_by_target_subject(subject_id)

    activities_and_flows = await ActivityService(session, user.id).get_activity_and_flow_basic_info_by_ids_or_auto(
        applet_id=applet_id,
        ids=activity_and_flow_ids_from_submissions + activity_and_flow_ids_from_assignments,
        include_auto=not is_limited_respondent,
        language=language,
    )

    result = []
    for activity_or_flow in activities_and_flows:
        activity_or_flow_assignments = [
            assignment
            for assignment in assignments
            if assignment.activity_id == activity_or_flow.id or assignment.activity_flow_id == activity_or_flow.id
        ]

        activity_or_flow.set_status(assignments=activity_or_flow_assignments, include_auto=True)

        result.append(
            ActivityOrFlowWithAssignmentsPublic(
                **activity_or_flow.dict(),
                assignments=activity_or_flow_assignments,
            )
        )

    return ResponseMulti(
        result=result,
        count=len(result),
    )


async def applet_activities_for_respondent_subject(
    applet_id: uuid.UUID,
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[ActivityOrFlowWithAssignmentsPublic]:
    applet_service = AppletService(session, user.id)
    await applet_service.exist_by_id(applet_id)

    subject = await SubjectsService(session, user.id).exist_by_id(subject_id)
    is_limited_respondent = subject.user_id is None

    # Restrict the endpoint access to owners, managers, coordinators, and assigned reviewers
    await CheckAccessService(session, user.id).check_subject_subject_access(applet_id, subject_id)

    assignments = await ActivityAssignmentService(session).get_all_with_subject_entities(
        applet_id, QueryParams(filters={"respondent_subject_id": subject_id})
    )

    # Only one of these IDs will be `None` at a time, so the resulting type will be a list of UUIDs
    activity_and_flow_ids_from_assignments: list[uuid.UUID] = [
        assignment.activity_id or assignment.activity_flow_id  # type: ignore
        for assignment in assignments
    ]

    activity_and_flow_ids_from_submissions = await AnswerService(
        session, user.id, answer_session
    ).get_activity_and_flow_ids_by_source_subject(subject_id)

    activities_and_flows = await ActivityService(session, user.id).get_activity_and_flow_basic_info_by_ids_or_auto(
        applet_id=applet_id,
        ids=activity_and_flow_ids_from_submissions + activity_and_flow_ids_from_assignments,
        include_auto=not is_limited_respondent,
        language=language,
    )

    result: list[ActivityOrFlowWithAssignmentsPublic] = []
    for activity_or_flow in activities_and_flows:
        activity_or_flow_assignments = [
            assignment
            for assignment in assignments
            if assignment.activity_id == activity_or_flow.id or assignment.activity_flow_id == activity_or_flow.id
        ]

        activity_or_flow.set_status(assignments=activity_or_flow_assignments, include_auto=not is_limited_respondent)

        result.append(
            ActivityOrFlowWithAssignmentsPublic(
                **activity_or_flow.dict(),
                assignments=activity_or_flow_assignments,
            )
        )

    return ResponseMulti(
        result=result,
        count=len(result),
    )


async def applet_activities_and_flows(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AppletActivityFilter)),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[AppletActivitiesAndFlowsDetailsPublic]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

        filters = AppletActivityFilter(**query_params.filters)

        activities_future = ActivityService(session, user.id).get_single_language_with_items_by_applet_id(
            applet_id, language
        )
        flows_future = FlowService(session).get_full_flows(applet_id)

        activities, flows = await asyncio.gather(activities_future, flows_future)

        if filters.has_submitted or filters.has_score:
            activities = await __filter_activities(
                activities, applet_id, user.id, filters, language, session, answer_session
            )

    result = AppletActivitiesAndFlowsDetailsPublic(
        details=activities + flows,
    )
    return Response(result=result)


async def __filter_activities(
    activities: list[ActivityLanguageWithItemsMobileDetailPublic],
    applet_id: uuid.UUID,
    user_id: uuid.UUID,
    filters: AppletActivityFilter,
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> list[ActivityLanguageWithItemsMobileDetailPublic]:
    for activity in activities:
        # Filter by `hasSubmitted` (if the activity has submitted answers)
        if filters.has_submitted is not None:
            latest_answer = await AnswerService(session, user_id, answer_session).get_latest_answer_by_activity_id(
                applet_id, activity.id
            )
            if filters.has_submitted:
                if latest_answer is None:
                    activities.remove(activity)
            else:
                if latest_answer is not None:
                    activities.remove(activity)

        # Filter by `hasScore` (if the activity has score set to activity items)
        if filters.has_score is not None:
            activity_items = await ActivityItemService(session).get_single_language_by_activity_id(
                activity.id, language
            )

            found_score = False
            for activity_item in activity_items:
                if found_score:
                    break

                options = getattr(activity_item.response_values, "options", [])
                for option in options:
                    if option.score > 0:
                        found_score = True

            if filters.has_score:
                if not found_score:
                    activities.remove(activity)
            else:
                if found_score:
                    activities.remove(activity)

    return activities


async def applet_activities_metadata_for_subject(
    applet_id: uuid.UUID,
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> Response[ActivitiesMetadata]:
    applet_service = AppletService(session, user.id)
    await applet_service.exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

    subject = await SubjectsService(session, user.id).exist_by_id(subject_id)
    is_limited_respondent = subject.user_id is None

    # Fetch assigned activity or flow IDs for the subject
    assigned_activities = await ActivityAssignmentService(session).get_assigned_activity_or_flow_ids_for_subject(
        subject_id
    )

    # Fetch activities submissions by the subject
    submissions_metadata = await AnswerService(session, user.id, answer_session).get_submissions_metadata_by_subject(
        subject_id
    )

    # Fetch auto-assigned activity and flow IDs by applet ID
    auto_activity_ids = await ActivityService(session, user.id).get_activity_and_flow_ids_by_applet_id_auto(applet_id)

    # Combine all assigned IDs and submitted activity IDs
    all_activity_ids = (
        set(assigned_activities.activities.keys())
        | set(submissions_metadata.activities.keys())
        | set(auto_activity_ids)
    )

    activities = await ActivitiesCRUD(session).get_by_applet_id_and_activities_ids(applet_id, list(all_activity_ids))
    flows = await FlowsCRUD(session).get_by_applet_id_and_flows_ids(applet_id, list(all_activity_ids))

    activities_state = {activity.id: activity.soft_exists() for activity in activities}
    flows_state = {flow.id: flow.soft_exists() for flow in flows}

    # Initialize ActivitiesCounters with zero counts
    activities_metadata = ActivitiesMetadata(subject_id=subject_id)

    # Iterate over all activity or flow IDs
    for activity_or_flow_id in all_activity_ids:
        is_auto = activity_or_flow_id in auto_activity_ids

        # Get submission and assignment data if available
        submission_data = submissions_metadata.activities.get(activity_or_flow_id)
        assignments_data = assigned_activities.activities.get(activity_or_flow_id)

        # Initialize sets for respondents and subjects
        respondents = set()
        subjects = set()

        # Initialize submission counts
        respondent_submissions_count = 0
        subject_submissions_count = 0
        last_submission_date = None

        # Update from submission data
        if submission_data:
            respondents.update(submission_data.respondents)
            subjects.update(submission_data.subjects)
            respondent_submissions_count = submission_data.respondent_submissions_count
            subject_submissions_count = submission_data.subject_submissions_count
            last_submission_date = submission_data.last_submission_date

        # Update from assignment data
        if assignments_data:
            respondents.update(assignments_data.respondents)
            subjects.update(assignments_data.subjects)

        # Include the subject for auto-assigned activities, excluding limited accounts
        if is_auto and not is_limited_respondent:
            respondents.add(subject_id)
            subjects.add(subject_id)

        # Calculate counts
        respondents_count = len(respondents)
        subjects_count = len(subjects)

        activity_or_flow_exists = activities_state.get(activity_or_flow_id) or flows_state.get(activity_or_flow_id)

        # Update activities counters counts
        if subjects_count > 0:
            if activity_or_flow_exists:
                activities_metadata.respondent_activities_count_existing += 1
            else:
                activities_metadata.respondent_activities_count_deleted += 1
        if respondents_count > 0:
            if activity_or_flow_exists:
                activities_metadata.target_activities_count_existing += 1
            else:
                activities_metadata.target_activities_count_deleted += 1

        # Append the activity subject counters
        activities_metadata.activities_or_flows.append(
            ActivitySubjectMetadata(
                activity_or_flow_id=activity_or_flow_id,
                respondents_count=respondents_count,
                subjects_count=subjects_count,
                respondent_submissions_count=respondent_submissions_count,
                subject_submissions_count=subject_submissions_count,
                last_submission_date=last_submission_date,
            )
        )

    return Response(result=activities_metadata)
