from fastapi.routing import APIRouter

from apps.items.api.item_templates import (
    create_item_template,
    delete_item_template_by_id,
    get_item_templates,
)

router = APIRouter(prefix="/items", tags=["Items"])

router.get("/templates")(get_item_templates)
router.post("/templates")(create_item_template)
router.delete("/templates/{id_}")(delete_item_template_by_id)
