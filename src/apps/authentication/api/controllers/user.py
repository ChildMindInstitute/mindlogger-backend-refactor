from fastapi import APIRouter, Body

from apps.authentication.services.security import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.domain import PublicUser, UserCreate, UserSignUpRequest
from apps.users.errors import UserNotFound, UsersError
from apps.users.services import UsersCRUD

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", tags=["Authentication"])
async def create_user(
    user_create_schema: UserSignUpRequest = Body(...),
) -> Response[PublicUser]:
    try:
        await UsersCRUD().get_by_email(email=user_create_schema.email)
        raise UsersError("User already exist")
    except UserNotFound:
        user_in_db = UserCreate(
            email=user_create_schema.email,
            full_name=user_create_schema.full_name,
            hashed_password=AuthenticationService.get_password_hash(
                user_create_schema.password
            ),
        )
        user, _ = await UsersCRUD().save_user(schema=user_in_db)

    # Create public user model in order to avoid password sharing
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)
