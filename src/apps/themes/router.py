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
router.delete("/{id_}")(delete_theme_by_id)
router.put("/{id_}")(update_theme_by_id)
