import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.integrations.domain import Integration
from apps.integrations.service import IntegrationService
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

__all__ = ["create_integration", "retrieve_integration", "delete_integration"]


async def create_integration(
    session=Depends(get_session),
    user: User = Depends(get_current_user),
    integrationsCreate: Integration = Body(...),
) -> Integration:
    await CheckAccessService(session, user.id).check_integrations_access(integrationsCreate.applet_id)
    async with atomic(session):
        return await IntegrationService(session, user).create_integration(integrationsCreate)


async def retrieve_integration(
    integration_type: str,
    applet_id: uuid.UUID,
    session=Depends(get_session),
    user: User = Depends(get_current_user),
) -> Integration:
    await CheckAccessService(session, user.id).check_integrations_access(applet_id)
    async with atomic(session):
        return await IntegrationService(session, user).retrieve_integration(applet_id, integration_type)


async def delete_integration(
    integration_type: str,
    applet_id: uuid.UUID,
    session=Depends(get_session),
    user: User = Depends(get_current_user),
):
    await CheckAccessService(session, user.id).check_integrations_access(applet_id)
    async with atomic(session):
        await IntegrationService(session, user).delete_integration_by_type(applet_id, integration_type)
