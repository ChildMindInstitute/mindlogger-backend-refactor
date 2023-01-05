from fastapi.routing import APIRouter

from apps.users.api.users import (
    change_password,
    create_user,
    delete_user,
    get_user,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])

router.post("")(create_user)
router.get("/me")(get_user)
router.put("/me")(update_user)
router.delete("/me")(delete_user)
router.post("/me/password/change")(change_password)
