import uuid

from fastapi import Body, Depends
from starlette.requests import Request

from apps.applets.service import AppletService
from apps.audit import AuditEvent, EventAction, http_audit_fields, log
from apps.authentication.deps import get_current_user
from apps.shared.exception import BaseError
from apps.transfer_ownership.domain import InitiateTransfer
from apps.transfer_ownership.service import TransferService
from apps.users import UserNotFound
from apps.users.domain import User
from apps.users.services.user import UserService
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def transfer_initiate(
    applet_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    transfer: InitiateTransfer = Body(...),
    session=Depends(get_session),
) -> None:
    """Initiate a transfer of ownership of an applet."""
    target_owner_id: uuid.UUID | None = None
    try:
        async with atomic(session):
            try:
                # Resolve the proposed new owner for audit log
                target_owner = await UserService(session).get_by_email(transfer.email)
                target_owner_id = target_owner.id
            except UserNotFound:
                # Transferring to an email without an user account
                pass

            await AppletService(session, user.id).exist_by_id(applet_id)
            await CheckAccessService(session, user.id).check_create_transfer_ownership_access(applet_id)
            await TransferService(session, user).initiate_transfer(applet_id, transfer)
    except BaseError as e:
        await log(
            AuditEvent(
                event_action=EventAction.APPLET_TRANSFER_INITIATE,
                user_id=user.id,
                curious_applet_id=[applet_id],
                user_target_id=target_owner_id,
                user_target_email=None if target_owner_id else transfer.email,
                user_target_roles=[Role.OWNER],
                **http_audit_fields(request, e),
            )
        )
        raise

    await log(
        AuditEvent(
            event_action=EventAction.APPLET_TRANSFER_INITIATE,
            user_id=user.id,
            curious_applet_id=[applet_id],
            user_target_id=target_owner_id,
            user_target_email=None if target_owner_id else transfer.email,
            user_target_roles=[Role.OWNER],
            **http_audit_fields(request),
        )
    )


async def transfer_accept(
    applet_id: uuid.UUID,
    key: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Respond to a transfer of ownership of an applet."""
    try:
        async with atomic(session):
            await TransferService(session, user).accept_transfer(applet_id, key)
    except BaseError as e:
        await log(
            AuditEvent(
                event_action=EventAction.APPLET_TRANSFER_ACCEPT,
                user_id=user.id,
                curious_applet_id=[applet_id],
                user_target_id=user.id,
                user_target_roles=[Role.OWNER],
                **http_audit_fields(request, e),
            )
        )
        raise

    await log(
        AuditEvent(
            event_action=EventAction.APPLET_TRANSFER_ACCEPT,
            user_id=user.id,
            curious_applet_id=[applet_id],
            user_target_id=user.id,
            user_target_roles=[Role.OWNER],
            **http_audit_fields(request),
        )
    )


async def transfer_decline(
    applet_id: uuid.UUID,
    key: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    """Decline a transfer of ownership of an applet."""
    try:
        async with atomic(session):
            await TransferService(session, user).decline_transfer(applet_id, key)
    except BaseError as e:
        await log(
            AuditEvent(
                event_action=EventAction.APPLET_TRANSFER_DECLINE,
                user_id=user.id,
                curious_applet_id=[applet_id],
                user_target_id=user.id,
                **http_audit_fields(request, e),
            )
        )
        raise

    await log(
        AuditEvent(
            event_action=EventAction.APPLET_TRANSFER_DECLINE,
            user_id=user.id,
            curious_applet_id=[applet_id],
            user_target_id=user.id,
            **http_audit_fields(request),
        )
    )
