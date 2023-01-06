from fastapi.routing import APIRouter

from apps.users.api import (
    password_recovery,
    password_recovery_approve,
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
router.post("/me/password/recover")(password_recovery)
router.post("/me/password/recover/approve")(password_recovery_approve)
