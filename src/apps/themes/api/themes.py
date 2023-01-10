from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.themes.crud import ThemesCRUD
from apps.themes.domain import (
    PublicTheme,
    Theme,
    ThemeCreate,
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
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicTheme]:
    """Returns all themes."""

    themes: list[PublicTheme] = await ThemesCRUD().get_all()

    return ResponseMulti(results=themes)


async def delete_theme_by_id(pk: int, user: User = Depends(get_current_user)):
    await ThemesCRUD().delete_by_id(pk=pk, creator_id=user.id)
    raise NotContentError


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
