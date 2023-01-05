from fastapi.routing import APIRouter

from apps.themes.api.themes import (
    create_theme,
    delete_theme_by_id,
    get_themes,
    update_theme_by_id,
)

router = APIRouter(prefix="/themes", tags=["Themes"])

router.get("")(get_themes)
router.post("")(create_theme)
router.delete("/{pk}")(delete_theme_by_id)
router.put("/{pk}")(update_theme_by_id)
