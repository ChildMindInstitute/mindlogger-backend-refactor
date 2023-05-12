import uuid

from sqlalchemy import select, case
from sqlalchemy.orm import Query

from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database import BaseCRUD


class AppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def has_role(
            self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> bool:
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == role)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def has_any_roles(
            self, applet_id: uuid.UUID, user_id: uuid.UUID, roles: list[Role]
    ) -> bool:
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def get_priority_role(
            self, applet_id: uuid.UUID, user_id: uuid.UUID
    ) -> Role | None:
        query: Query = select(UserAppletAccessSchema.role)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.order_by(
            case(
                (UserAppletAccessSchema.role == Role.OWNER, 1),
                (UserAppletAccessSchema.role == Role.MANAGER, 2),
                (UserAppletAccessSchema.role == Role.COORDINATOR, 3),
                (UserAppletAccessSchema.role == Role.EDITOR, 4),
                (UserAppletAccessSchema.role == Role.REVIEWER, 5),
                (UserAppletAccessSchema.role == Role.RESPONDENT, 6),
                else_=10,
            ).asc()
        )
        query = query.limit(1)
        db_result = await self._execute(query)
        result = db_result.scalars().first()

        return Role(result) if result else None

    async def can_edit_applet(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. Create an applet
        2. Upload new content
        3. Duplicate
        4. Edit, save or delete applet
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.editors())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_invite_anyone(
            self, applet_id: uuid.UUID, user_id: uuid.UUID
    ):
        """
        Organizer [Manager, Coordinator, Editor, Reviewer]
        1. invite new organizer to lower role
        2. can view all organizers
        3. change organizers role/permission where lower role
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.inviters())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_invite(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. invite new respondent
        2. can view all respondents
        3. remove access from lower role
        4. invite new reviewer
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.inviters())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_set_schedule_and_notifications(
            self, applet_id: uuid.UUID, user_id: uuid.UUID
    ):
        """
        1. set schedule and notifications to respondents
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.inviters())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_see_any_data(
            self, applet_id: uuid.UUID, user_id: uuid.UUID
    ):
        """
        1. view all users data
        2. delete users data
        2. export any users data
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.super_reviewers())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_see_data(
            self, applet_id: uuid.UUID, user_id: uuid.UUID
    ):
        """
        1. view assigned users data
        2. export assigned users data
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.reviewers())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()
