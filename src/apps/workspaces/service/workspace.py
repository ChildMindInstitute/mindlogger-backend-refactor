import uuid
from typing import Tuple

from pydantic import ValidationError

from apps.applets.crud import AppletsCRUD
from apps.shared.query_params import QueryParams
from apps.users import User, UsersCRUD
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import (
    AnswerDbApplet,
    AnswerDbApplets,
    WorkspaceApplet,
    WorkspaceArbitrary,
    WorkspaceArbitraryCreate,
    WorkspaceArbitraryFields,
    WorkspaceInfo,
    WorkspaceManager,
    WorkspaceRespondent,
    WorkspaceSearchApplet,
)
from apps.workspaces.errors import (
    ArbitraryServerSettingsError,
    WorkspaceAccessDenied,
    WorkspaceDoesNotExistError,
    WorkspaceNotFoundError,
)
from apps.workspaces.service.check_access import CheckAccessService
from apps.workspaces.service.user_access import UserAccessService


class WorkspaceService:
    def __init__(self, session, user_id: uuid.UUID):
        self._user_id = user_id
        self.session = session

    async def create_workspace_from_user(self, user: User) -> UserWorkspaceSchema:
        schema = await UserWorkspaceCRUD(self.session).save(
            UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=f"{user.first_name} {user.last_name}",
                is_modified=False,
            )
        )
        return schema

    async def get_workspace(self, user_id: uuid.UUID) -> WorkspaceInfo:
        await self.has_access(
            user_id,
            self._user_id,
            [
                Role.OWNER,
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
            ],
        )
        schema = await UserWorkspaceCRUD(self.session).get_by_user_id(self._user_id)
        has_managers = await UserAppletAccessCRUD(self.session).has_managers(self._user_id)
        return WorkspaceInfo(name=schema.workspace_name, has_managers=has_managers)

    async def has_access(self, user_id: uuid.UUID, owner_id: uuid.UUID, roles: list[Role]):
        has_access = await UserAppletAccessCRUD(self.session).has_access(user_id, owner_id, roles)
        if not has_access:
            raise WorkspaceAccessDenied()

    async def update_workspace_name(self, user: User, workspace_prefix: str | None = None):
        """
        Let's check if the workspace name has changed before.
        We don't do anything. Otherwise, accept the workspace prefix value
        and update the workspace name. This procedure is performed only once.
        You can't change the workspace name after that.
        """
        user_workspace = await UserWorkspaceCRUD(self.session).get_by_user_id(user.id)
        if not user_workspace:
            user_workspace = await self.create_workspace_from_user(user)
        if not user_workspace.is_modified and workspace_prefix:
            user_workspace.workspace_name = workspace_prefix
            await UserWorkspaceCRUD(self.session).update_by_user_id(
                user.id,
                user_workspace,
            )

    async def get_workspace_respondents(
        self,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceRespondent], int, list[str]]:
        users, total, ordering_fields = await UserAppletAccessCRUD(self.session).get_workspace_respondents(
            self._user_id, owner_id, applet_id, query_params
        )
        return users, total, ordering_fields

    async def get_workspace_applet_respondents_total(self, applet_id: uuid.UUID) -> int:
        await CheckAccessService(self.session, self._user_id).check_applet_respondent_list_access(applet_id)

        total = await UserAppletAccessCRUD(self.session).get_applet_respondents_total(applet_id)

        return total

    async def get_workspace_managers(
        self,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceManager], int, list[str]]:
        # TODO: Investigate if we do need the search by email
        # hash the email is exist in the search
        # if query_params.search and EMAIL_REGEX.match(query_params.search):
        #     query_params.search = hash_sha224(query_params.search)

        users, total, ordering_fields = await UserAppletAccessCRUD(self.session).get_workspace_managers(
            self._user_id, owner_id, applet_id, query_params
        )

        return users, total, ordering_fields

    async def get_workspace_applets(
        self, owner_id: uuid.UUID, language: str, query_params: QueryParams
    ) -> list[WorkspaceApplet]:
        folder_or_applets = []
        applets_crud = AppletsCRUD(self.session)
        if query_params.filters.get("flat_list"):
            workspace_applets = await applets_crud.get_applets_flat_list(owner_id, self._user_id, query_params)
        else:
            workspace_applets = await applets_crud.get_workspace_applets(owner_id, self._user_id, query_params)
        for folder_or_applet in workspace_applets:
            folder_or_applets.append(
                WorkspaceApplet(
                    id=folder_or_applet[0],
                    display_name=folder_or_applet[1],
                    image=folder_or_applet[2],
                    is_pinned=folder_or_applet[3],
                    encryption=folder_or_applet[4],
                    created_at=folder_or_applet[5],
                    updated_at=folder_or_applet[6],
                    version=folder_or_applet[7],
                    type=folder_or_applet[8],
                    role=folder_or_applet[9],
                    folders_applet_count=folder_or_applet[10],
                    description=folder_or_applet[12],
                    activity_count=folder_or_applet[13],
                    owner_id=owner_id,
                )
            )
        return folder_or_applets

    async def search_workspace_applets(
        self,
        owner_id: uuid.UUID,
        search_text,
        language: str,
        query_params: QueryParams,
    ) -> list[WorkspaceSearchApplet]:
        folder_or_applets = []
        workspace_applets = await AppletsCRUD(self.session).search_workspace_applets(
            owner_id, self._user_id, search_text, query_params
        )
        for folder_or_applet in workspace_applets:
            folder_or_applets.append(
                WorkspaceSearchApplet(
                    id=folder_or_applet[0],
                    display_name=folder_or_applet[1],
                    image=folder_or_applet[2],
                    is_pinned=False,
                    encryption=folder_or_applet[3],
                    created_at=folder_or_applet[4],
                    updated_at=folder_or_applet[5],
                    version=folder_or_applet[6],
                    type="applet",
                    role=folder_or_applet[7],
                    folder_id=folder_or_applet[8],
                    folder_name=folder_or_applet[9],
                    owner_id=owner_id,
                )
            )
        return folder_or_applets

    async def search_workspace_applets_count(
        self,
        owner_id: uuid.UUID,
        search_text,
    ) -> int:
        count = await AppletsCRUD(self.session).search_workspace_applets_count(owner_id, self._user_id, search_text)

        return count

    async def get_workspace_applets_count(self, owner_id: uuid.UUID, query: QueryParams) -> int:
        applet_crud = AppletsCRUD(self.session)
        if query.filters["flat_list"]:
            count = await applet_crud.get_workspace_applets_flat_list_count(owner_id, self._user_id)
        else:
            count = await applet_crud.get_workspace_applets_count(owner_id, self._user_id)
        return count

    async def get_workspace_folder_applets(
        self, owner_id: uuid.UUID, folder_id: uuid.UUID, language: str
    ) -> list[WorkspaceApplet]:
        schemas = await AppletsCRUD(self.session).get_folders_applets(owner_id, self._user_id, folder_id)

        applets = []
        for schema, is_pinned in schemas:
            applets.append(
                WorkspaceApplet(
                    id=schema.id,
                    display_name=schema.display_name,
                    image=schema.image,
                    is_pinned=is_pinned,
                    encryption=schema.encryption,
                    created_at=schema.created_at,
                    updated_at=schema.updated_at,
                    version=schema.version,
                    type="applet",
                    folders_applet_count=0,
                    owner_id=owner_id,
                )
            )

        applet_ids = [applet.id for applet in applets]

        workspace_applets = []
        workspace_applet_map = dict()
        for applet in applets:
            workspace_applet = WorkspaceApplet.from_orm(applet)
            workspace_applet_map[workspace_applet.id] = workspace_applet
            workspace_applets.append(workspace_applet)

        applet_role_map = await UserAccessService(self.session, self._user_id).get_applets_roles_by_priority(applet_ids)

        for applet_id, role in applet_role_map.items():
            workspace_applet_map[applet_id].role = role
        return workspace_applets

    async def exists_by_owner_id(self, owner_id: uuid.UUID):
        exists = await UsersCRUD(self.session).exist_by_key("id", owner_id)
        if not exists:
            raise WorkspaceDoesNotExistError()

    async def get_applets_roles_by_priority(self, owner_id, applet_ids):
        # check if applets exist
        for applet_id in applet_ids:
            await CheckAccessService(self.session, self._user_id).check_applet_detail_access(applet_id)

        return await UserAppletAccessCRUD(self.session).get_applets_roles_by_priority_for_workspace(
            owner_id, self._user_id, applet_ids
        )

    async def get_arbitrary_info_if_use_arbitrary(self, applet_id: uuid.UUID) -> WorkspaceArbitrary | None:
        schema = await UserWorkspaceCRUD(self.session).get_by_applet_id(applet_id)
        if not schema or not schema.use_arbitrary or not schema.database_uri:
            return None
        try:
            return WorkspaceArbitrary.from_orm(schema) if schema else None
        except ValidationError:
            return None

    async def get_arbitrary_info_by_owner_id_if_use_arbitrary(self, owner_id: uuid.UUID) -> WorkspaceArbitrary | None:
        schema = await UserWorkspaceCRUD(self.session).get_by_user_id(owner_id)
        if not schema or not schema.use_arbitrary or not schema.database_uri:
            return None
        try:
            return WorkspaceArbitrary.from_orm(schema) if schema else None
        except ValidationError:
            return None

    async def get_arbitraries_map(self, applet_ids: list[uuid.UUID]) -> dict[str | None, list[uuid.UUID]]:
        """Returning map {"arbitrary_uri": [applet_ids]}"""
        return await UserWorkspaceCRUD(self.session).get_arbitraries_map_by_applet_ids(applet_ids)

    async def get_user_answer_db_info(self) -> list[AnswerDbApplets]:
        db_info = await UserWorkspaceCRUD(self.session).get_user_answers_db_info(self._user_id)

        # group by db_uri. None means default DB
        db_applets_map: dict[str | None, AnswerDbApplets] = {}
        for row in db_info:
            db_uri = None
            if row.use_arbitrary:
                if not row.database_uri:
                    continue
                db_uri = row.database_uri
            if db_uri not in db_applets_map:
                db_applets_map[db_uri] = AnswerDbApplets(database_uri=db_uri)
            db_applets_map[db_uri].applets.append(AnswerDbApplet(applet_id=row.applet_id, encryption=row.encryption))

        # default db first
        default_db_applets = db_applets_map.pop(None, None)
        if default_db_applets:
            return [default_db_applets, *db_applets_map.values()]

        return list(db_applets_map.values())

    async def set_arbitrary_server(
        self, data: WorkspaceArbitraryCreate | WorkspaceArbitraryFields, *, rewrite=False
    ) -> None:
        repository = UserWorkspaceCRUD(self.session)
        schema = await repository.get_by_user_id(self._user_id)
        if not schema:
            raise WorkspaceNotFoundError("Workspace not found")
        arbitrary_data = WorkspaceArbitraryFields.from_orm(schema)
        if not arbitrary_data.is_arbitrary_empty() and not rewrite:
            raise ArbitraryServerSettingsError(arbitrary_data, "Arbitrary settings are already set")
        for k, v in data.dict(by_alias=False).items():
            setattr(schema, k, v)
        await repository.update_by_user_id(schema.user_id, schema)

    async def get_arbitrary_list(self) -> list[WorkspaceArbitrary]:
        schemas = await UserWorkspaceCRUD(self.session).get_arbitrary_list()
        if not schemas:
            return []
        return [WorkspaceArbitrary.from_orm(schema) for schema in schemas]

    async def get_workspace_subjects(
        self,
        owner_id: uuid.UUID,
        applet_id: uuid.UUID | None,
        query_params: QueryParams,
    ) -> Tuple[list[WorkspaceRespondent], int, list[str]]:
        users, total, sortable_fields = await UserAppletAccessCRUD(self.session).get_workspace_respondents(
            self._user_id, owner_id, applet_id, query_params
        )
        return users, total, sortable_fields
