from fastapi.routing import APIRouter

from apps.users.api.users import (
    password_update,
    user_create,
    user_delete,
    user_retrieve,
    user_update,
)

router = APIRouter(prefix="/users", tags=["Users"])

router.post("")(user_create)
router.get("/me")(user_retrieve)
router.put("/me")(user_update)
router.delete("/me")(user_delete)
router.put("/me/password")(password_update)
