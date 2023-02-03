from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.themes.crud import ThemesCRUD
from apps.themes.domain import (
    PublicTheme,
    Theme,
    ThemeCreate,
    ThemeQueryParams,
    ThemeRequest,
    ThemeUpdate,
)
from apps.users.domain import User


async def create_theme(
    user: User = Depends(get_current_user),
    schema: ThemeRequest = Body(...),
) -> Response[Theme]:
    theme: Theme = await ThemesCRUD().save(
        schema=ThemeCreate(
            **schema.dict(), public=False, allow_rename=False, creator=user.id
        )
    )

    return Response(result=PublicTheme(**theme.dict()))


async def get_themes(
    query_params: QueryParams = Depends(parse_query_params(ThemeQueryParams)),
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicTheme]:
    """Returns all themes."""
    themes: list[PublicTheme] = await ThemesCRUD().list(query_params)
    return ResponseMulti(result=themes)


async def delete_theme_by_id(pk: int, user: User = Depends(get_current_user)):
    await ThemesCRUD().delete_by_id(pk=pk, creator_id=user.id)


async def update_theme_by_id(
    pk: int,
    user: User = Depends(get_current_user),
    schema: ThemeRequest = Body(...),
) -> Response[PublicTheme]:
    theme: Theme = await ThemesCRUD().update(
        pk=pk,
        update_schema=ThemeUpdate(
            **schema.dict(), public=False, allow_rename=False
        ),
        creator_id=user.id,
    )
    return Response(result=PublicTheme(**theme.dict()))
