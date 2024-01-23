import uuid

from apps.logs.crud.user_activity_log import UserActivityLogCRUD
from apps.logs.db.schemas import UserActivityLogSchema
from infrastructure.http.domain import MindloggerContentSource


class UserActivityLogService:
    def __init__(self, session):
        self.session = session

    async def create_log(
        self,
        user_id: uuid.UUID,
        firebase_token_id: str | None,
        event_type: str,
        event: str,
        user_agent: str | None,
        mindlogger_content: str,
    ) -> UserActivityLogSchema:
        # TODO: remove this remporary solution when mobile is ready
        if (
            mindlogger_content == MindloggerContentSource.undefined.name
            and firebase_token_id
        ):
            mindlogger_content = MindloggerContentSource.mobile.name
        schema = UserActivityLogSchema(
            user_id=user_id,
            firebase_token_id=firebase_token_id,
            event_type=event_type,
            event=event,
            user_agent=user_agent,
            mindlogger_content=mindlogger_content,
        )
        return await UserActivityLogCRUD(self.session).save(schema)
