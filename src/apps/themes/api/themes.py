import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.themes.domain import PublicTheme, ThemeQueryParams, ThemeRequest
from apps.themes.service import ThemeService
from apps.users.domain import User


async def create_theme(
    user: User = Depends(get_current_user),
    schema: ThemeRequest = Body(...),
) -> Response[PublicTheme]:
    """Creates a new theme."""
    theme: PublicTheme = await ThemeService(user.id).create(schema)
    return Response(result=theme)


async def get_themes(
    query_params: QueryParams = Depends(parse_query_params(ThemeQueryParams)),
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicTheme]:
    """Returns all themes."""
    themes: list[PublicTheme] = await ThemeService(user.id).get_all(
        query_params
    )
    return ResponseMulti(result=themes, count=len(themes))


async def delete_theme_by_id(
    pk: uuid.UUID, user: User = Depends(get_current_user)
):
    """Deletes a theme by id."""
    await ThemeService(user.id).delete_by_id(pk)


async def update_theme_by_id(
    pk: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ThemeRequest = Body(...),
) -> Response[PublicTheme]:
    theme: PublicTheme = await ThemeService(user.id).update(pk, schema)

    return Response(result=theme)
