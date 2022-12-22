from fastapi.routing import APIRouter

from apps.authentication.api.auth import access_token_delete, get_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.post("/token")(get_access_token)
router.delete("/token")(access_token_delete)
