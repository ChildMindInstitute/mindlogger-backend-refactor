import asyncio
import json
import uuid
from typing import List

from pydantic import parse_obj_as

from apps.activities.crud import ActivityHistoriesCRUD, ActivityItemHistoriesCRUD
from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.activity_flows.crud import FlowItemHistoriesCRUD, FlowsHistoryCRUD
from apps.activity_flows.db.schemas import ActivityFlowItemHistorySchema
from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD
from apps.library.crud import CartCRUD, LibraryCRUD
from apps.library.db import CartSchema, LibrarySchema
from apps.library.domain import (
    AppletLibraryCreate,
    AppletLibraryFull,
    AppletLibraryInfo,
    AppletLibraryUpdate,
    Cart,
    LibraryItem,
    LibraryItemActivity,
    LibraryItemActivityItem,
    LibraryItemFlow,
    LibraryItemFlowItem,
    PublicLibraryItem,
)
from apps.library.errors import (
    AppletNameExistsError,
    AppletVersionDoesNotExistError,
    AppletVersionExistsError,
    LibraryItemDoesNotExistError,
)
from apps.shared.paging import paging_list
from apps.shared.query_params import QueryParams
from apps.workspaces.service.check_access import CheckAccessService
from config import settings


class LibraryService:
    def __init__(self, session):
        self.session = session

    async def check_applet_name(self, name: str) -> None:
        """Check if applet with this name is already in library."""
        name_exists = await LibraryCRUD(self.session).check_applet_name(name)
        if name_exists:
            raise AppletNameExistsError()

    async def share_applet(self, schema: AppletLibraryCreate) -> AppletLibraryFull:
        """Share applet to library."""

        # check if applet with this name is already in library
        await self.check_applet_name(schema.name)

        # if not, check if library_item.name is same as applet.display_name
        applet = await AppletsCRUD(self.session).get_by_id(id_=schema.applet_id)
        applet_version = f"{schema.applet_id}_{applet.version}"
        # check if this applet version is already in library
        library_item = await LibraryCRUD(self.session).exist_by_key(key="applet_id_version", val=applet_version)
        if library_item:
            raise AppletVersionExistsError()

        if applet.display_name != schema.name:
            # if not, update applet.display_name to library_item.name
            # in applet and applet_history
            await AppletsCRUD(self.session).update_display_name(applet_id=schema.applet_id, display_name=schema.name)

            await AppletHistoriesCRUD(self.session).update_display_name(
                id_version=applet_version,
                display_name=schema.name,
            )

        search_keywords = await self._get_search_keywords(applet, applet_version)
        search_keywords.append(schema.name)
        # save library_item
        library_item = LibrarySchema(
            applet_id_version=f"{schema.applet_id}_{applet.version}",
            keywords=schema.keywords,
            search_keywords=search_keywords,
        )
        library_item = await LibraryCRUD(self.session).save(library_item)

        return AppletLibraryFull.from_orm(library_item)

    async def _get_search_keywords(self, applet, applet_version):
        search_keywords = []
        search_keywords.extend(applet.description.values())

        activities = await ActivityHistoriesCRUD(session=self.session).retrieve_by_applet_version(applet_version)

        search_keywords.extend([activity.name for activity in activities])

        activity_items = await ActivityItemHistoriesCRUD(self.session).get_by_activity_id_versions(
            [activity.id_version for activity in activities]
        )

        for activity_item in activity_items:
            search_keywords.extend(activity_item.question.values())
            if activity_item.response_type in ["singleSelect", "multiSelect"]:
                options = activity_item.response_values.get("options")
                search_keywords.extend([option["text"] for option in options])
        return search_keywords

    async def get_applets_count(self, query_param: QueryParams) -> int:
        count = await LibraryCRUD(self.session).get_all_library_count(query_param)
        return count

    async def get_all_applets(self, query_params: QueryParams) -> list[PublicLibraryItem]:
        """Get all applets for library."""

        library_schemas = await LibraryCRUD(self.session).get_all_library_items(query_params)
        library_items = parse_obj_as(list[LibraryItem], library_schemas)

        for library_item in library_items:
            library_item = await self._get_full_library_item(library_item)

        return [
            PublicLibraryItem(
                version=library_item.applet_id_version.split("_")[1],
                **library_item.dict(exclude={"applet_id_version"}),
            )
            for library_item in library_items
        ]

    async def get_applet_by_id(self, id_: uuid.UUID) -> PublicLibraryItem:
        """Get applet detail for library by id."""

        library_item = await LibraryCRUD(self.session).get_library_item_by_id(id_)

        library_item = await self._get_full_library_item(library_item)
        return PublicLibraryItem(
            version=library_item.applet_id_version.split("_")[1],
            **library_item.dict(exclude={"applet_id_version"}),
        )

    async def _get_full_library_item(self, library_item: LibraryItem) -> LibraryItem:
        activities = await ActivityHistoriesCRUD(session=self.session).retrieve_by_applet_version(
            library_item.applet_id_version
        )
        library_item_activities = []
        activity_id_key_maps = dict()
        activity_id_versions = [activity.id_version for activity in activities]
        all_activity_items = await ActivityItemHistoriesCRUD(self.session).get_by_activity_id_versions(
            activity_id_versions
        )
        activity_items_map: dict[str, list[ActivityItemHistorySchema]] = dict()
        for activity_item in all_activity_items:
            activity_items_map.setdefault(f"{activity_item.activity_id}", []).append(activity_item)

        for activity in activities:
            activity_items = activity_items_map[activity.id_version]
            activity_id_key_maps[activity.id_version] = uuid.uuid4()
            items = [
                LibraryItemActivityItem(
                    name=item.name,
                    question=item.question,
                    response_type=item.response_type,
                    response_values=self._get_response_value_options(item.response_values),
                    config=item.config,
                    is_hidden=item.is_hidden,
                    conditional_logic=item.conditional_logic,
                    allow_edit=item.allow_edit,
                )
                for item in activity_items
            ]
            library_item_activities.append(
                LibraryItemActivity(
                    key=activity_id_key_maps[activity.id_version],
                    name=activity.name,
                    description=activity.description,
                    image=activity.image,
                    splash_screen=activity.splash_screen,
                    show_all_at_once=activity.show_all_at_once,
                    is_skippable=activity.is_skippable,
                    is_reviewable=activity.is_reviewable,
                    is_performance_task=activity.is_performance_task,
                    performance_task_type=activity.performance_task_type,
                    response_is_editable=activity.response_is_editable,
                    is_hidden=activity.is_hidden,
                    scores_and_reports=activity.scores_and_reports,
                    subscale_setting=activity.subscale_setting,
                    items=items,
                )
            )
        library_item.activities = library_item_activities

        flows = await FlowsHistoryCRUD(session=self.session).retrieve_by_applet_version(library_item.applet_id_version)
        flow_id_versions = [flow.id_version for flow in flows]
        all_flow_items = await FlowItemHistoriesCRUD(self.session).get_by_flow_ids(flow_id_versions)
        flow_items_map: dict[str, list[ActivityFlowItemHistorySchema]] = dict()
        for flow_item in all_flow_items:
            flow_items_map.setdefault(f"{flow_item.activity_flow_id}", []).append(flow_item)

        library_item_flows = []

        for flow in flows:
            flow_items = flow_items_map[flow.id_version]
            library_item_flows.append(
                LibraryItemFlow(
                    name=flow.name,
                    description=flow.description,
                    is_single_report=flow.is_single_report,
                    hide_badge=flow.hide_badge,
                    is_hidden=flow.is_hidden,
                    items=[
                        LibraryItemFlowItem(
                            activity_key=activity_id_key_maps[item.activity_id],
                        )
                        for item in flow_items
                    ],
                )
            )
        library_item.activity_flows = library_item_flows
        return library_item

    def _get_response_value_options(self, response_values):
        if response_values:
            if "options" in response_values:
                for option in response_values["options"]:
                    option.pop("id", None)
                return response_values
        return response_values

    async def get_applet_url(self, applet_id: uuid.UUID) -> AppletLibraryInfo:
        """Get applet url for library by id."""
        applet = await AppletsCRUD(self.session).get_by_id(id_=applet_id)
        applet_version = f"{applet_id}_{applet.version}"
        library_item = await LibraryCRUD(self.session).get_by_applet_id_version(applet_version)
        if not library_item:
            raise AppletVersionDoesNotExistError()

        domain = settings.service.urls.frontend.admin_base
        return AppletLibraryInfo(
            url=f"https://{domain}/library/{library_item.id}",
            library_id=library_item.id,
        )

    async def update_shared_applet(
        self,
        library_id: uuid.UUID,
        schema: AppletLibraryUpdate,
        user_id: uuid.UUID,
    ):
        library = await LibraryCRUD(self.session).get_by_id(id=library_id)
        if not library:
            raise LibraryItemDoesNotExistError()

        # check if user has access to
        applet_id = uuid.UUID(str(library.applet_id_version).split("_")[0])

        await CheckAccessService(self.session, user_id).check_applet_share_library_access(applet_id=applet_id)

        applet = await AppletsCRUD(self.session).get_by_id(id_=applet_id)
        new_applet_version = f"{applet_id}_{applet.version}"

        # if applet name is new, check if applet with this name is already in library  # noqa E501
        if applet.display_name != schema.name:
            await self.check_applet_name(schema.name)
            await AppletsCRUD(self.session).update_display_name(applet_id=applet_id, display_name=schema.name)

            await AppletHistoriesCRUD(self.session).update_display_name(
                id_version=new_applet_version,
                display_name=schema.name,
            )
        search_keywords = await self._get_search_keywords(applet, new_applet_version)
        search_keywords.append(schema.name)

        # save library_item
        library_item = LibrarySchema(
            applet_id_version=new_applet_version,
            keywords=schema.keywords,
            search_keywords=search_keywords,
        )
        library_item = await LibraryCRUD(self.session).update(library_item, library_id)
        return AppletLibraryFull.from_orm(library_item)

    async def get_cart(self, user_id: uuid.UUID) -> Cart:
        """Get cart for user."""
        cart = await CartCRUD(self.session).get_by_user_id(user_id)
        if not cart or not cart.cart_items:
            return Cart(cart_items=None)
        return Cart(cart_items=json.loads(cart.cart_items))

    async def add_to_cart(self, user_id: uuid.UUID, schema: Cart) -> Cart:
        """Add item to cart."""

        cart_schema = await CartCRUD(self.session).get_by_user_id(user_id)
        if not cart_schema:
            cart_schema = CartSchema(user_id=user_id, cart_items=None)
        if schema.cart_items:
            cart_schema.cart_items = json.dumps(schema.cart_items)
        else:
            cart_schema.cart_items = None

        cart = await CartCRUD(self.session).save(cart_schema)

        return Cart(cart_items=json.loads(cart.cart_items) if cart.cart_items else None)

    @staticmethod
    async def _search_in_cart(pattern: str, item: dict) -> bool:
        pattern = pattern.lower()
        parsed_item = PublicLibraryItem.parse_obj(item)
        if pattern in parsed_item.display_name.lower():
            return True

        if parsed_item.keywords:
            for keyword in parsed_item.keywords:
                if pattern in keyword.lower():
                    return True
                await asyncio.sleep(0)

        if parsed_item.activities:
            for activity in parsed_item.activities:
                if pattern in activity.name.lower():
                    return True
                await asyncio.sleep(0)
        return False

    async def filter_cart_items(self, cart: Cart | None, query_params: QueryParams) -> List[PublicLibraryItem]:
        if not cart:  # pragma: no cover
            return []
        filtered_items: list[dict] = []
        if query_params.search and cart.cart_items:
            for item in cart.cart_items:
                if await self._search_in_cart(query_params.search, item):
                    filtered_items.append(item)

        items = paging_list(
            filtered_items if query_params.search else cart.cart_items,
            page=query_params.page,
            limit=query_params.limit,
        )
        return parse_obj_as(List[PublicLibraryItem], items)
