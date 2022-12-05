from fastapi.routing import APIRouter

from apps.authentication.api.auth import (
    access_token_delete,
    create_user,
    get_access_token,
    refresh_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.post("/signup")(create_user)
router.post("/access-token")(get_access_token)
router.post("/signout")(access_token_delete)
router.post("/refresh-access-token")(refresh_access_token)
