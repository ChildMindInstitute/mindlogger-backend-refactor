from apps.applets.crud import AppletHistoriesCRUD
from apps.applets.domain import History


async def retrieve_versions(applet_id: int) -> list[History]:
    applet_versions = await AppletHistoriesCRUD().retrieve_versions_by_applet_id(
        applet_id
    )
    versions = []
    for version, created_at, user_schema in applet_versions:
        versions.append(
            History(
                version=version,
                created_at=created_at,
                creator=dict(
                    id=user_schema.id, full_name=user_schema.full_name
                ),
            )
        )
    return versions
