from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.items.crud.item_templates import ItemTemplatesCRUD
from apps.items.domain.item_templates import (
    ItemTemplate,
    ItemTemplateCreate,
    ItemTemplateInitializeCreate,
    PublicItemTemplate,
)
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


async def create_item_template(
    user: User = Depends(get_current_user),
    schema: ItemTemplateInitializeCreate = Body(...),
) -> Response[PublicItemTemplate]:

    item_template: ItemTemplate = await ItemTemplatesCRUD().save(
        schema=ItemTemplateCreate(**schema.dict(), user_id=user.id)
    )

    return Response(result=PublicItemTemplate(**item_template.dict()))


async def delete_item_template_by_id(
    id_: int, user: User = Depends(get_current_user)
):
    await ItemTemplatesCRUD().delete_by_id(id_=id_)
    raise NotContentError


async def get_item_templates(
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicItemTemplate]:
    item_templates: list[
        PublicItemTemplate
    ] = await ItemTemplatesCRUD().get_item_templates(user.id)

    return ResponseMulti(results=item_templates)
