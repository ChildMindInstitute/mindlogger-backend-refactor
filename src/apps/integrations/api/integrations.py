from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.integrations.domain import Integration, IntegrationFilter
from apps.integrations.service import IntegrationService
from apps.shared.domain import ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

__all__ = ["enable_integration", "disable_integration"]


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
