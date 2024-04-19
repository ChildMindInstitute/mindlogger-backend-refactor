from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.logs.services import UserActivityLogService
from apps.users.db.schemas import UserSchema
from infrastructure.http.domain import MindloggerContentSource


async def test_create_log_success(session: AsyncSession, tom: UserSchema, base_log_data: dict[str, Any]) -> None:
    base_log_data["user_id"] = tom.id
    log = await UserActivityLogService(session).create_log(**base_log_data)
    assert log.user_id == tom.id


async def test_create_log_undefined_with_device_is_mobile_content(
    session: AsyncSession, tom: UserSchema, base_log_data: dict[str, Any]
) -> None:
    base_log_data["user_id"] = tom.id
    base_log_data["firebase_token_id"] = "token"
    base_log_data["mindlogger_content"] = MindloggerContentSource.undefined
    log = await UserActivityLogService(session).create_log(**base_log_data)
    assert log.mindlogger_content == MindloggerContentSource.mobile
