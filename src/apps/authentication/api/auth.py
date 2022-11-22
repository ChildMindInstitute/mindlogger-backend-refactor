from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from apps.users.db.schemas import UserCreate
from apps.users.domain.models import User
from apps.users.services.crud import UsersCRUD
from infrastructure.database.core import get_session

router = APIRouter(tags=["Auth"])


@router.post("/user/signup", response_model=User)
async def create_user(
    *,
    db: Session = get_session(),
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    """
    user = UsersCRUD.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = UsersCRUD.save_user(db, obj_in=user_in)

    return user
