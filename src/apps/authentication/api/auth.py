from datetime import timedelta
from fastapi import Body, HTTPException, status
from fastapi.responses import Response
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Any
from fastapi import Depends
from fastapi.responses import JSONResponse

from apps.authentication.db.schemas import TokenData
from apps.authentication.services import get_password_hash, verify_password, create_access_token, create_refresh_token
from apps.users.services.crud import UsersCRUD
from apps.users.domain import User, UserCreate, UserInDB, UsersError, UserLogin
from config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["Authentication"])


@router.get("/test", status_code=status.HTTP_200_OK)
def get_for_test():
    return Response("Test - OK!")


@router.post("/login/test-token", response_model=User, tags=["Authentication"])
async def test_token_get_current_user(token: str = Body(...)) -> Any:
    """
    Test access token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.authentication.secret_key, algorithms=[settings.authentication.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    current_user: User = await UsersCRUD().get_by_email(email=token_data.email)
    if current_user is None:
        raise credentials_exception
    return current_user


@router.post("/user/signup", tags=["Authentication"])
async def create_user(user_create_schema: UserCreate = Body(...)):
    try:
        user: User = await UsersCRUD().get_by_email(email=user_create_schema.email)
        if user:
            raise HTTPException(
                status_code=400,
                detail=f"The user with email={user_create_schema.email} already exists in the system.",
            )
    except UsersError:
        user_in_db = UserInDB(
            email=user_create_schema.email,
            username=user_create_schema.username,
            hashed_password=get_password_hash(user_create_schema.password)
        )
        user, is_created = await UsersCRUD().save_user(schema=user_in_db)

    return user


async def authenticate_user(user_login_schema: UserLogin = Body(...)):
    try:
        user: User = await UsersCRUD().get_by_email(email=user_login_schema.email)
    except UsersError:
        raise HTTPException(
            status_code=400,
            detail=f"The user with email={user_login_schema.email} not exists in the system.",
        )
    if not verify_password(user_login_schema.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid password",
        )
    return user


@router.post("/user/signin", tags=["Authentication"])
async def login_for_access_token(user_login_schema: UserLogin = Body(...)):
    user: User = await authenticate_user(user_login_schema)
    access_token_expires = timedelta(
        minutes=settings.authentication.access_token_expire_minutes
    )
    refresh_token_expires = timedelta(
        minutes=settings.authentication.refresh_token_expire_minutes
    )
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
