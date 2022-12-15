from fastapi.routing import APIRouter

from apps.users.api import delete_user, get_user, update_user

router = APIRouter(prefix="/users", tags=["Users"])

router.get("/me")(get_user)
router.put("/me")(update_user)
router.delete("/me")(delete_user)
