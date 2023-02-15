from fastapi.routing import APIRouter
from starlette import status

from apps.activities.api.activities import activity_retrieve
from apps.activities.api.reusable_item_choices import (
    item_choice_create,
    item_choice_delete,
    item_choice_retrieve,
)
from apps.activities.domain.reusable_item_choices import (
    PublicReusableItemChoice,
)
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)

router = APIRouter(prefix="/activities", tags=["Activities"])

router.post(
    "/item_choices",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[PublicReusableItemChoice],
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicReusableItemChoice]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(item_choice_create)

router.get(
    "/item_choices",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicReusableItemChoice],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicReusableItemChoice]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(item_choice_retrieve)

router.delete(
    "/item_choices/{id_}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(item_choice_delete)

router.get("/{id_}")(activity_retrieve)
