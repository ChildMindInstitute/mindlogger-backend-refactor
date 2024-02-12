import uuid

from fastapi import Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.deps.preprocess_arbitrary import (
    get_answer_session_by_subject,
)
from apps.answers.service import AnswerService
from apps.authentication.deps import get_current_user
from apps.invitations.errors import NonUniqueValue
from apps.shared.domain import Response
from apps.shared.exception import NotFoundError, ValidationError
from apps.shared.response import EmptyResponse
from apps.subjects.domain import (
    Subject,
    SubjectCreateRequest,
    SubjectDeleteRequest,
    SubjectReadResponse,
    SubjectRelationCreate,
    SubjectUpdateRequest,
)
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def create_subject(
    user: User = Depends(get_current_user),
    schema: SubjectCreateRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> Response[Subject]:
    await CheckAccessService(session, user.id).check_applet_invite_access(
        schema.applet_id
    )
    async with atomic(session):
        subject_sch = Subject(
            applet_id=schema.applet_id,
            creator_id=user.id,
            language=schema.language,
            first_name=schema.first_name,
            last_name=schema.last_name,
            nickname=schema.nickname,
            secret_user_id=schema.secret_user_id,
            email=schema.email,
        )
        subject = await SubjectsService(session, user.id).create(subject_sch)
        return Response(result=Subject.from_orm(subject))


async def create_relation(
    subject_id: uuid.UUID,
    source_subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: SubjectRelationCreate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    service = SubjectsService(session, user.id)
    source_subject = await service.get(source_subject_id)
    target_subject = await service.get(subject_id)
    if not source_subject or not source_subject.soft_exists():
        raise NotFoundError(f"Subject {source_subject_id} not found")
    if not target_subject or not target_subject.soft_exists():
        raise NotFoundError(f"Subject {subject_id} not found")
    if source_subject.applet_id != target_subject.applet_id:
        raise ValidationError("applet_id doesn't match")

    await CheckAccessService(session, user.id).check_applet_invite_access(
        target_subject.applet_id
    )
    async with atomic(session):
        await service.create_relation(
            subject_id,
            source_subject_id,
            schema.relation,
        )
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
    await CheckAccessService(session, user.id).check_applet_invite_access(
        subject.applet_id
    )
    async with atomic(session):
        await service.delete_relation(subject_id, source_subject_id)
        return EmptyResponse()


async def update_subject(
    subject_id: uuid.UUID,
    schema: SubjectUpdateRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response[Subject]:
    subject_srv = SubjectsService(session, user.id)
    subject = await subject_srv.get(subject_id)
    if not subject:
        raise NotFoundError()
    await CheckAccessService(session, user.id).check_subject_edit_access(
        subject.applet_id
    )
    exist = await subject_srv.check_secret_id(
        subject_id, schema.secret_user_id, subject.applet_id
    )
    if exist:
        raise NonUniqueValue()
    async with atomic(session):
        subject.secret_user_id = schema.secret_user_id
        subject.nickname = schema.nickname
        subject = await subject_srv.update(subject)
        return Response(result=Subject.from_orm(subject))


async def delete_subject(
    subject_id: uuid.UUID,
    params: SubjectDeleteRequest = Body(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    arbitrary_session: AsyncSession | None = Depends(
        get_answer_session_by_subject
    ),
):
    subject_srv = SubjectsService(session, user.id)
    subject = await subject_srv.get(subject_id)
    if not subject:
        raise NotFoundError()
    # Check that user has right on applet
    await UserAccessService(session, user.id).validate_subject_delete_access(
        subject.applet_id
    )
    async with atomic(session):
        # Remove respondent role for user
        await UserAppletAccessService(
            session, user.id, subject.applet_id
        ).remove_access_by_user_and_applet_to_role(
            subject.user_id, subject.applet_id, Role.RESPONDENT
        )

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


async def get_subject(
    subject_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response[SubjectReadResponse]:
    subject = await SubjectsService(session, user.id).get(subject_id)
    if not subject:
        raise NotFoundError()
    await CheckAccessService(session, user.id).check_subject_subject_access(
        subject.applet_id, subject_id
    )
    return Response(
        result=SubjectReadResponse(
            secret_user_id=subject.secret_user_id, nickname=subject.nickname
        )
    )
