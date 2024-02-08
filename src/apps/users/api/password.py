import uuid
from typing import Annotated

from fastapi import Body, Depends, Query
from pydantic import Required
from starlette import status

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.job.service import JobService
from apps.shared.domain.response import Response
from apps.shared.response import EmptyResponse
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    ChangePasswordRequest,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryRequest,
    PublicUser,
    User,
    UserChangePassword,
)
from apps.users.errors import ReencryptionInProgressError, UserNotFound
from apps.users.services import PasswordRecoveryCache, PasswordRecoveryService
from apps.users.tasks import reencrypt_answers
from config import settings
from infrastructure.cache import CacheNotFound, PasswordRecoveryHealthCheckNotValid
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def password_update(
    user: User = Depends(get_current_user),
    schema: ChangePasswordRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    """General endpoint for update password for signin."""
    reencryption_in_progress = await JobService(session, user.id).is_job_in_progress("reencrypt_answers")
    if reencryption_in_progress:
        raise ReencryptionInProgressError()

    async with atomic(session):
        AuthenticationService.verify_password(
            schema.prev_password,
            user.hashed_password,
        )

        password_hash: str = AuthenticationService.get_password_hash(schema.password)
        password = UserChangePassword(hashed_password=password_hash)

        updated_user: User = await UsersCRUD(session).change_password(user, password)

        # Create public representation of the internal user
        public_user = PublicUser.from_user(updated_user)

    email = user.email_encrypted
    retries = settings.task_answer_encryption.max_retries
    await reencrypt_answers.kiq(user.id, email, schema.prev_password, schema.password, retries=retries)

    return Response[PublicUser](result=public_user)


async def password_recovery(
    schema: PasswordRecoveryRequest = Body(...),
    session=Depends(get_session),
) -> EmptyResponse:
    """General endpoint for sending password recovery email
    and stored info in Redis.
    """
    # Send the password recovery the internal password recovery service
    async with atomic(session):
        try:
            await PasswordRecoveryService(session).send_password_recovery(schema)
        except UserNotFound:
            pass  # mute error in terms of user enumeration vulnerability

    return EmptyResponse(status_code=status.HTTP_201_CREATED)


async def password_recovery_approve(
    schema: PasswordRecoveryApproveRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    """General endpoint to approve the password recovery."""

    # Approve the password recovery
    # NOTE: also check if the data exists and tokens are not expired
    async with atomic(session):
        public_user: PublicUser = await PasswordRecoveryService(session).approve(schema)

    return Response[PublicUser](result=public_user)


async def password_recovery_healthcheck(
    email: Annotated[str, Query(max_length=100)] = Required,
    key: Annotated[uuid.UUID | str, Query(max_length=36)] = Required,
) -> None:
    """General endpoint to get the password recovery healthcheck."""

    try:
        await PasswordRecoveryCache().get(email, key)
    except CacheNotFound:
        raise PasswordRecoveryHealthCheckNotValid()
