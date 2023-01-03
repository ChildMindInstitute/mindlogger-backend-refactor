from fastapi.routing import APIRouter

from apps.activities.api.reusable_item_choices import (
    create_item_choice,
    delete_item_choice_by_id,
    get_item_choices,
)

router = APIRouter(prefix="/activity", tags=["Activities"])

router.post("/item_choices")(create_item_choice)
router.get("/item_choices")(get_item_choices)
router.delete("/item_choices/{id_}", status_code=204)(delete_item_choice_by_id)
