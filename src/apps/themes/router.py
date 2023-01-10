from fastapi.routing import APIRouter

from apps.themes.api.themes import (
    create_theme,
    delete_theme_by_id,
    get_themes,
    update_theme_by_id,
)

router = APIRouter(prefix="/themes", tags=["Themes"])

router.get("")(get_themes)
router.post("", status_code=201)(create_theme)
router.delete("/{pk}", status_code=204)(delete_theme_by_id)
router.put("/{pk}", status_code=200)(update_theme_by_id)
