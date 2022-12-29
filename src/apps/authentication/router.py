from fastapi.routing import APIRouter

from apps.authentication.api.auth import (
    delete_access_token,
    get_token,
    refresh_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.post("/token")(get_token)
router.delete("/token")(delete_access_token)
router.post("/token/refresh")(refresh_access_token)
