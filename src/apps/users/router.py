from fastapi.routing import APIRouter

from apps.users.api import (
    get_user_me,
    update_user_me,
    delete_user_me,
)

router = APIRouter(prefix="/users", tags=["Users"])

router.get("/me")(get_user_me)
router.put("/me")(update_user_me)
router.delete("/me")(delete_user_me)
