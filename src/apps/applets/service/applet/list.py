from apps.applets.crud import AppletsCRUD
from apps.applets.domain import Role
from apps.applets.domain.applets import detail


# TODO: getting user related applets, not admins applet
async def get_admin_applets(user_id: int):
    applet_schemas = await AppletsCRUD().get_applets_by_roles(
        user_id, [Role.ADMIN]
    )
    return [detail.Applet.from_orm(schema) for schema in applet_schemas]
