from fastapi import HTTPException
from apps.users.db.schemas import UserCreate
from apps.users.services.crud import UsersCRUD

from fastapi import status
from fastapi import Body
from fastapi.responses import Response
from apps.users.domain.models import UserSchema
from apps.authentication.api.auth_handler import signJWT

from fastapi.routing import APIRouter


router = APIRouter(tags=["Authentication"])


@router.get("/test", status_code=status.HTTP_200_OK)
def get_for_test():
    return Response("Test - OK!")


@router.post("/user/signup", tags=["user"])
async def create_user(user: UserCreate = Body(...)):
    user = UsersCRUD.get_by_email(UserSchema(), email=user.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = UsersCRUD.save_user(UserSchema(), schema=UserCreate())
    user, is_created = user
    return signJWT(user.email)
