from fastapi import Body, Depends

from apps.activities.crud.reusable_item_choices import ReusabelItemChoiceCRUD
from apps.activities.domain.reusable_item_choices import (
    PublicReusableItemChoice,
    ReusableItemChoice,
    ReusableItemChoiceCreate,
    ReusableItemChoiceInitializeCreate,
)
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


async def create_item_choice(
    user: User = Depends(get_current_user),
    schema: ReusableItemChoiceInitializeCreate = Body(...),
) -> Response[PublicReusableItemChoice]:

    item_template: ReusableItemChoice = await ReusabelItemChoiceCRUD().save(
        schema=ReusableItemChoiceCreate(**schema.dict(), user_id=user.id)
    )

    return Response(result=PublicReusableItemChoice(**item_template.dict()))


async def delete_item_choice_by_id(
    id_: int, user: User = Depends(get_current_user)
):
    await ReusabelItemChoiceCRUD().delete_by_id(id_=id_)
    raise NotContentError


async def get_item_choices(
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicReusableItemChoice]:
    item_templates: list[
        PublicReusableItemChoice
    ] = await ReusabelItemChoiceCRUD().get_item_templates(user.id)

    return ResponseMulti(results=item_templates)
