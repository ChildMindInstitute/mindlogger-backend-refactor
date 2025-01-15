import uuid
from datetime import datetime, timedelta
from typing import TypedDict

from fastapi import Body, Depends
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_assignments.service import ActivityAssignmentService
from apps.answers.deps.preprocess_arbitrary import get_answer_session, get_answer_session_by_subject
from apps.answers.service import AnswerService
from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.invitations.errors import NonUniqueValue
from apps.invitations.services import InvitationsService
from apps.shared.domain import Response, ResponseMulti
from apps.shared.exception import NotFoundError, ValidationError
from apps.shared.response import EmptyResponse
from apps.shared.subjects import is_take_now_relation, is_valid_take_now_relation
from apps.subjects.domain import (
    Subject,
    SubjectCreate,
    SubjectCreateRequest,
    SubjectDeleteRequest,
    SubjectReadResponse,
    SubjectRelationCreate,
    SubjectUpdateRequest,
    TargetSubjectByRespondentResponse,
)
from apps.subjects.errors import SecretIDUniqueViolationError
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.users.services.user import UserService
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def create_subject(
    user: User,
    schema: SubjectCreateRequest,
    session: AsyncSession,
) -> Response[Subject]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(schema.applet_id)
        await CheckAccessService(session, user.id).check_applet_invite_access(schema.applet_id)
        service = SubjectsService(session, user.id)

        try:
            subject = await service.create(SubjectCreate(creator_id=user.id, **schema.dict(by_alias=False)))
        except SecretIDUniqueViolationError:
            wrapper = ErrorWrapper(
                ValueError(NonUniqueValue()), ("body", SubjectCreateRequest.field_alias("secret_user_id"))
            )
            raise RequestValidationError([wrapper])

        return Response(result=subject)


async def create_relation(
    subject_id: uuid.UUID,
    source_subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: SubjectRelationCreate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    service = SubjectsService(session, user.id)
    source_subject = await service.get_if_soft_exist(source_subject_id)
    target_subject = await service.get_if_soft_exist(subject_id)
    if not source_subject:
        raise NotFoundError(f"Subject {source_subject_id} not found")
    if not target_subject:
        raise NotFoundError(f"Subject {subject_id} not found")
    if source_subject.applet_id != target_subject.applet_id:
        raise ValidationError("applet_id doesn't match")

    await CheckAccessService(session, user.id).check_applet_invite_access(target_subject.applet_id)

    existing_relation = await service.get_relation(source_subject_id, subject_id)
    if is_take_now_relation(existing_relation):
        await service.delete_relation(subject_id, source_subject_id)

    async with atomic(session):
        await service.create_relation(
            subject_id,
            source_subject_id,
            schema.relation,
        )
        return EmptyResponse()


async def create_temporary_multiinformant_relation(
    subject_id: uuid.UUID,
    source_subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = SubjectsService(session, user.id)
    source_subject = await service.get_if_soft_exist(source_subject_id)
    target_subject = await service.get_if_soft_exist(subject_id)
    if not source_subject:
        raise NotFoundError(f"Subject {source_subject_id} not found")
    if not target_subject:
        raise NotFoundError(f"Subject {subject_id} not found")
    if source_subject.applet_id != target_subject.applet_id:
        raise ValidationError("applet_id doesn't match")

    check_access_service = CheckAccessService(session, user.id)

    # Only owners and managers can initiate take now from the admin panel
    await check_access_service.check_applet_manager_list_access(target_subject.applet_id)

    existing_relation = await service.get_relation(source_subject_id, subject_id)
    if existing_relation:
        if existing_relation.relation != "take-now" or existing_relation.meta is None:
            # There is already a non-temporary relation. Do nothing
            return EmptyResponse()

        expires_at = datetime.fromisoformat(existing_relation.meta["expiresAt"])
        if expires_at > datetime.now():
            # The current temporary relation is still valid. Do nothing
            return EmptyResponse()

        await service.delete_relation(subject_id, source_subject_id)

    async with atomic(session):
        expires_at = datetime.now() + timedelta(seconds=settings.multi_informant.temp_relation_expiry_secs)
        await service.create_relation(subject_id, source_subject_id, "take-now", {"expiresAt": expires_at.isoformat()})
        return EmptyResponse()


async def delete_relation(
    subject_id: uuid.UUID,
    source_subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = SubjectsService(session, user.id)
    subject = await service.get(subject_id)
    if not subject:
        raise NotFoundError()
    subject = await service.get(source_subject_id)
    if not subject:
        raise NotFoundError()
    await CheckAccessService(session, user.id).check_applet_invite_access(subject.applet_id)
    async with atomic(session):
        await service.delete_relation(subject_id, source_subject_id)
        return EmptyResponse()


async def update_subject(
    subject_id: uuid.UUID,
    schema: SubjectUpdateRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response[SubjectReadResponse]:
    subject_srv = SubjectsService(session, user.id)
    subject = await subject_srv.get(subject_id)
    if not subject:
        raise NotFoundError()
    await CheckAccessService(session, user.id).check_subject_edit_access(subject.applet_id)
    exist = await subject_srv.check_secret_id(subject_id, schema.secret_user_id, subject.applet_id)
    if exist:
        raise NonUniqueValue()
    async with atomic(session):
        subject.secret_user_id = schema.secret_user_id
        subject.nickname = schema.nickname
        subject = await subject_srv.update(subject.id, **schema.dict(by_alias=False))
        return Response(
            result=SubjectReadResponse(
                secret_user_id=subject.secret_user_id,
                nickname=subject.nickname,
                id=subject.id,
                tag=subject.tag,
                applet_id=subject.applet_id,
                user_id=subject.user_id,
                first_name=subject.first_name,
                last_name=subject.last_name,
            )
        )


async def delete_subject(
    subject_id: uuid.UUID,
    params: SubjectDeleteRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    arbitrary_session: AsyncSession | None = Depends(get_answer_session_by_subject),
):
    subject_srv = SubjectsService(session, user.id)
    subject = await subject_srv.get(subject_id)
    if not subject:
        raise NotFoundError()
    # Check that user has right on applet
    await UserAccessService(session, user.id).validate_subject_delete_access(subject.applet_id)
    async with atomic(session):
        if params.delete_answers:
            # Remove subject and answers
            await SubjectsService(session, user.id).delete_hard(subject.id)
            async with atomic(arbitrary_session):
                await AnswerService(
                    user_id=user.id,
                    session=session,
                    arbitrary_session=arbitrary_session,
                ).delete_by_subject(subject_id)
        else:
            # Delete subject (soft)
            await SubjectsService(session, user.id).delete(subject.id)

        uaa_repository = UserAppletAccessService(session, user.id, subject.applet_id)
        # remove pinned subject
        await uaa_repository.unpin(pinned_user_id=subject.user_id, pinned_subject_id=subject.id)

        if subject.user_id:
            ex_resp = await UserService(session).get(subject.user_id)
            if ex_resp:
                await InvitationsService(session, ex_resp).delete_for_respondents([subject.applet_id])
            # Remove respondent role for user
            await uaa_repository.remove_access_by_user_and_applet_to_role(
                subject.user_id, subject.applet_id, Role.RESPONDENT
            )


async def get_subject(
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    arbitrary_session: AsyncSession | None = Depends(get_answer_session_by_subject),
) -> Response[SubjectReadResponse]:
    subjects_service = SubjectsService(session, user.id)
    subject = await subjects_service.get(subject_id)
    if not subject:
        raise NotFoundError()

    user_subject = await subjects_service.get_by_user_and_applet(user.id, subject.applet_id)
    if not user_subject:
        await CheckAccessService(session, user.id).check_subject_subject_access(subject.applet_id, subject_id)
    else:
        relation = await subjects_service.get_relation(user_subject.id, subject_id)
        has_relation = relation is not None and (
            relation.relation != "take-now" or is_valid_take_now_relation(relation)
        )
        if not has_relation:
            await CheckAccessService(session, user.id).check_subject_subject_access(subject.applet_id, subject_id)

    answer_dates = await AnswerService(
        user_id=user.id, session=session, arbitrary_session=arbitrary_session
    ).get_last_answer_dates([subject.id], subject.applet_id)

    return Response(
        result=SubjectReadResponse(
            id=subject.id,
            secret_user_id=subject.secret_user_id,
            nickname=subject.nickname,
            last_seen=answer_dates.get(subject.id),
            tag=subject.tag,
            applet_id=subject.applet_id,
            user_id=subject.user_id,
            first_name=subject.first_name,
            last_name=subject.last_name,
        )
    )


async def get_my_subject(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    arbitrary_session: AsyncSession | None = Depends(get_answer_session),
) -> Response[SubjectReadResponse]:
    # Check if applet exists
    await AppletService(session, user.id).exist_by_id(applet_id)

    # Check if user has access to applet
    await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

    subject = await SubjectsService(session, user.id).get_by_user_and_applet(user.id, applet_id)
    if not subject:
        raise NotFoundError()

    answer_dates = await AnswerService(
        user_id=user.id, session=session, arbitrary_session=arbitrary_session
    ).get_last_answer_dates([subject.id], subject.applet_id)
    return Response(
        result=SubjectReadResponse(
            id=subject.id,
            secret_user_id=subject.secret_user_id,
            nickname=subject.nickname,
            last_seen=answer_dates.get(subject.id),
            tag=subject.tag,
            applet_id=subject.applet_id,
            user_id=subject.user_id,
            first_name=subject.first_name,
            last_name=subject.last_name,
        )
    )


async def get_target_subjects_by_respondent(
    respondent_subject_id: uuid.UUID,
    activity_or_flow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    answer_session=Depends(get_answer_session),
) -> ResponseMulti[TargetSubjectByRespondentResponse]:
    subjects_service = SubjectsService(session, user.id)
    respondent_subject = await subjects_service.exist_by_id(respondent_subject_id)
    is_limited_respondent = respondent_subject.user_id is None

    # Make sure the authenticated user has access to the subject
    await CheckAccessService(session, user.id).check_subject_subject_access(
        respondent_subject.applet_id, respondent_subject.id
    )

    assignment_service = ActivityAssignmentService(session)
    assignment_subject_ids = await assignment_service.get_target_subject_ids_by_respondent(
        respondent_subject_id=respondent_subject_id, activity_or_flow_ids=[activity_or_flow_id]
    )

    is_auto_assigned = await assignment_service.check_if_auto_assigned(activity_or_flow_id)
    if is_auto_assigned and not is_limited_respondent:
        assignment_subject_ids.append(respondent_subject_id)

    submission_data: list[tuple[uuid.UUID, int]] = await AnswerService(
        user_id=user.id, session=session, arbitrary_session=answer_session
    ).get_target_subject_ids_by_respondent_and_activity_or_flow(
        respondent_subject_id=respondent_subject_id, activity_or_flow_id=activity_or_flow_id
    )

    class SubjectInfo(TypedDict):
        currently_assigned: bool
        submission_count: int

    subject_info: dict[uuid.UUID, SubjectInfo] = {}
    for subject_id, submission_count in submission_data:
        subject_info[subject_id] = {"currently_assigned": False, "submission_count": submission_count}

    for subject_id in assignment_subject_ids:
        if subject_id not in subject_info:
            subject_info[subject_id] = {"currently_assigned": True, "submission_count": 0}
        else:
            subject_info[subject_id]["currently_assigned"] = True

    subjects: list[Subject] = await subjects_service.get_by_ids(list(subject_info.keys()))
    result: list[TargetSubjectByRespondentResponse] = []

    accesses = await UserAppletAccessService(
        session, applet_id=respondent_subject.applet_id, user_id=user.id
    ).get_applet_accesses()
    respondent_target_subject: TargetSubjectByRespondentResponse | None = None
    is_super_reviewer = any(access.role in Role.super_reviewers() for access in accesses)
    reviewer_access = next((access for access in accesses if access.role == Role.REVIEWER), None)
    is_regular_reviewer = reviewer_access is not None

    # Find the respondent subject in the list of subjects
    for subject in subjects:
        can_view_data = is_super_reviewer or (
            is_regular_reviewer and str(subject.id) in reviewer_access.meta.get("subjects", [])
        )

        target_subject = TargetSubjectByRespondentResponse(
            secret_user_id=subject.secret_user_id,
            nickname=subject.nickname,
            tag=subject.tag,
            id=subject.id,
            applet_id=subject.applet_id,
            user_id=subject.user_id,
            first_name=subject.first_name,
            last_name=subject.last_name,
            submission_count=subject_info[subject.id]["submission_count"],
            currently_assigned=subject_info[subject.id]["currently_assigned"],
            team_member_can_view_data=can_view_data,
        )

        if subject.id == respondent_subject_id:
            respondent_target_subject = target_subject
        else:
            result.append(target_subject)

    if respondent_target_subject:
        # TODO: If this endpoint is ever paginated, this logic will need to be moved to the query level
        result.insert(0, respondent_target_subject)

    return ResponseMulti(result=result, count=len(result))
