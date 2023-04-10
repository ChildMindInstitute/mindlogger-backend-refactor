import uuid

from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD
from apps.applets.domain import History


async def retrieve_versions(session, applet_id: uuid.UUID) -> list[History]:
    await AppletsCRUD().get_by_id(applet_id)
    applet_versions = await AppletHistoriesCRUD(
        session
    ).retrieve_versions_by_applet_id(applet_id)
    versions = []
    for version, created_at, user_schema in applet_versions:
        versions.append(
            History(
                version=version,
                created_at=created_at,
                creator=dict(
                    id=user_schema.id,
                    first_name=user_schema.first_name,
                    last_name=user_schema.last_name,
                ),
            )
        )
    return versions
