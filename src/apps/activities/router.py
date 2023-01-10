from fastapi.routing import APIRouter

from apps.activities.api.reusable_item_choices import (
    item_choice_create,
    item_choice_delete,
    item_choice_retrieve,
)

router = APIRouter(prefix="/activity", tags=["Activities"])

router.post("/item_choices", status_code=201)(item_choice_create)
router.get("/item_choices")(item_choice_retrieve)
router.delete("/item_choices/{id_}", status_code=204)(item_choice_delete)
