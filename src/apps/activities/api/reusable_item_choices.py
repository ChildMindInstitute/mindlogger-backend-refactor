import uuid

from fastapi import Body, Depends

from apps.activities.crud import ReusableItemChoiceCRUD
from apps.activities.domain.reusable_item_choices import (
    PublicReusableItemChoice,
    ReusableItemChoice,
    ReusableItemChoiceCreate,
    ReusableItemChoiceInitializeCreate,
)
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.users.domain import User
from infrastructure.database import atomic, session_manager


async def item_choice_create(
    user: User = Depends(get_current_user),
    schema: ReusableItemChoiceInitializeCreate = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicReusableItemChoice]:
    async with atomic(session):
        item_template: ReusableItemChoice = await ReusableItemChoiceCRUD(
            session
        ).save(
            schema=ReusableItemChoiceCreate(**schema.dict(), user_id=user.id)
        )

    return Response(result=PublicReusableItemChoice(**item_template.dict()))


async def item_choice_delete(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    # TODO: validate user access
    async with atomic(session):
        await ReusableItemChoiceCRUD(session).delete_by_id(id_=id_)


async def item_choice_retrieve(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicReusableItemChoice]:
    async with atomic(session):
        item_templates = await ReusableItemChoiceCRUD(
            session
        ).get_item_templates(user.id)
        count = await ReusableItemChoiceCRUD(session).get_item_templates_count(
            user.id
        )

    return ResponseMulti(result=item_templates, count=count)
