from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.integrations.domain import Integration, IntegrationFilter
from apps.integrations.loris.domain.loris_integrations import IntegrationsCreate
from apps.integrations.loris.domain.loris_projects import LorisProjects
from apps.integrations.service import IntegrationService
from apps.shared.domain import ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

__all__ = ["enable_integration", "disable_integration", "create_integration"]


async def enable_integration(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    integrations: list[Integration] = Body(...),
) -> ResponseMulti[Integration]:
    async with atomic(session):
        integrations = await IntegrationService(session, user).enable_integration(integrations)
    return ResponseMulti(result=integrations, count=len(integrations))


async def disable_integration(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(IntegrationFilter)),
):
    async with atomic(session):
        await IntegrationService(session, user).disable_integration(query_params)


async def create_integration(
    type: str,
    session=Depends(get_session),
    user: User = Depends(get_current_user),
    params: IntegrationsCreate = Body(...),
) -> LorisProjects:
    await CheckAccessService(session, user.id).check_integrations_create_access(params.applet_id, type)
    async with atomic(session):
        return await IntegrationService(session, user).create_integration(type, params)
