import uuid

from sqlalchemy import JSON, and_, case, exists, func, or_, select, text
from sqlalchemy.orm import Query

from apps.users import UserSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.user_applet_access import RespondentExportData
from infrastructure.database import BaseCRUD


class AppletAccessCRUD(BaseCRUD[UserAppletAccessSchema]):
    schema_class = UserAppletAccessSchema

    async def has_role(
        self, applet_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> bool:
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role == role)
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def has_any_roles_for_applet(
        self,
        applet_id: uuid.UUID,
        user_id: uuid.UUID,
        roles=None,
    ) -> bool:
        if roles is None:
            roles = Role.as_list()
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def check_export_access(
        self,
        applet_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            or_(
                UserAppletAccessSchema.role.in_([Role.OWNER, Role.MANAGER]),
                and_(
                    UserAppletAccessSchema.role == Role.REVIEWER,
                    func.json_array_length(
                        func.cast(
                            UserAppletAccessSchema.meta[text("'respondents'")],
                            JSON,
                        )
                    )
                    > 0,
                ),
            )
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def has_any_roles_for_workspace(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
        roles=None,
    ) -> bool:
        if roles is None:
            roles = Role.managers()
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(roles))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def get_workspace_priority_role(
        self,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Role | None:
        query: Query = select(UserAppletAccessSchema.role)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
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

    async def get_applets_priority_role(
        self,
        applet_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Role | None:
        query: Query = select(UserAppletAccessSchema.role)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
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

    async def can_create_applet(self, owner_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. Create an applet
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.owner_id == owner_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.editors()))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_edit_applet(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. Upload new content
        2. Duplicate
        3. Edit, save or delete applet
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.editors()))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_set_retention(
        self, applet_id: uuid.UUID, user_id: uuid.UUID
    ):
        """
        1. Set retention of an applet
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_([Role.OWNER, Role.MANAGER])
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
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.inviters()))
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
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.inviters()))
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
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.schedulers()))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_see_any_data(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. view all users data
        2. delete users data
        2. export any users data
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(
            UserAppletAccessSchema.role.in_(Role.super_reviewers())
        )
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def can_see_data(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        """
        1. view assigned users data
        2. export assigned users data
        """
        query: Query = select(UserAppletAccessSchema.id)
        query = query.where(UserAppletAccessSchema.soft_exists())
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.user_id == user_id)
        query = query.where(UserAppletAccessSchema.role.in_(Role.reviewers()))
        query = query.exists()

        db_result = await self._execute(select(query))
        return db_result.scalars().first()

    async def get_respondent_export_data(
        self, applet_id: uuid.UUID, respondent_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, RespondentExportData]:
        if not respondent_ids:
            return {}

        has_manager_role = (
            exists()
            .where(
                # no soft_exists check here
                UserAppletAccessSchema.user_id == UserSchema.id,
                UserAppletAccessSchema.applet_id == applet_id,
                UserAppletAccessSchema.role != Role.RESPONDENT,
            )
            .correlate(UserSchema)
        )

        query = (
            select(
                UserSchema.id,
                UserSchema.email,
                UserAppletAccessSchema.respondent_secret_id.label("secret_id"),  # type: ignore[attr-defined] # noqa: E501
                has_manager_role.label("is_manager"),
            )
            .outerjoin(
                UserAppletAccessSchema,
                and_(
                    UserAppletAccessSchema.user_id == UserSchema.id,
                    UserAppletAccessSchema.applet_id == applet_id,
                    UserAppletAccessSchema.role == Role.RESPONDENT,
                ),
            )
            .where(UserSchema.id.in_(respondent_ids))
        )

        db_result = await self._execute(query)
        data = db_result.all()

        return {row.id: RespondentExportData.from_orm(row) for row in data}
