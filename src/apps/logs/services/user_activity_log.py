from apps.logs.crud.user_activity_log import UserActivityLogCRUD
from apps.logs.db.schemas import UserActivityLogSchema


class UserActivityLogService:
    def __init__(self, session):
        self.session = session

    async def create_log(
        self, schema: UserActivityLogSchema
    ) -> UserActivityLogSchema:
        return await UserActivityLogCRUD(self.session).save(schema)
