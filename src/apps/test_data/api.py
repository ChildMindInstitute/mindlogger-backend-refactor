from fastapi import Depends

from apps.authentication.deps import get_current_user


async def generate_test_data(user=Depends(get_current_user)) -> None:
    pass
