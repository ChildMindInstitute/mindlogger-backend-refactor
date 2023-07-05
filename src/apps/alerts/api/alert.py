import asyncio
import json
import uuid
from contextlib import suppress
from copy import deepcopy

from fastapi import Body, Depends, WebSocket
from websockets.exceptions import ConnectionClosed

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain.alert import Alert, AlertPublic, AlertWSInternal
from apps.alerts.errors import AlertUpdateAccessDenied, AlertViewAccessDenied
from apps.alerts.filters import AlertConfigQueryParams
from apps.alerts.service.alert import AlertService
from apps.answers.domain import AppletAnswerCreate
from apps.authentication.deps import get_current_user, get_current_user_for_ws
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from config import settings
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def alerts_create(
    user: User = Depends(get_current_user),
    applet_answer: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
) -> None:
    # Check user permissions.
    # Only respondent role can create alert
    async with atomic(session):
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_answer.applet_id,
            [Role.RESPONDENT],
        )
        if not roles:
            raise AlertViewAccessDenied

        await AlertService(session, user.id).create_alert(applet_answer)

        return


async def alert_get_all_by_applet_id(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AlertConfigQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[AlertPublic]:
    # Check user permissions.
    # Only manager roles - (admin) can get alert
    async with atomic(session):
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_id,
            [Role.OWNER],
        )
        if not roles:
            raise AlertViewAccessDenied

        # Get all alert for specific applet
        instances = await AlertCRUD(session).get_by_applet_id(
            applet_id, deepcopy(query_params)
        )

        count = await AlertCRUD(session).get_by_applet_id_count(
            applet_id, deepcopy(query_params)
        )

    return ResponseMulti(
        result=[
            AlertPublic.from_orm(alert_config) for alert_config in instances
        ],
        count=count,
    )


async def alert_update_status_by_id(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[Alert]:
    async with atomic(session):
        alert_schema: AlertSchema = await AlertCRUD(session).get_by_id(
            alert_id
        )
        # Check user permissions.
        # Only manager roles - (admin) can update alert status
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            alert_schema.applet_id,
            [Role.OWNER],
        )
        if not roles:
            raise AlertUpdateAccessDenied

        # Update specific alert
        instance = await AlertCRUD(session).update(alert_schema)

    alert = Alert(**instance.dict())

    return Response(result=alert)


async def ws_alert_get_all_by_applet_id(
    websocket: WebSocket,
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user_for_ws),
    session=Depends(get_session),
):
    await websocket.accept(websocket.headers.get("sec-websocket-protocol"))

    # SEND THE HISTORICAL DATA
    async with atomic(session):
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_id,
            [Role.OWNER],
        )
        if not roles:
            raise AlertViewAccessDenied

        # Get all alert for specific applet
        instances = await AlertCRUD(session).get_by_applet_id(applet_id)
        count = await AlertCRUD(session).get_by_applet_id_count(applet_id)

    last_sent_alerts: dict[uuid.UUID, AlertWSInternal] = {
        instance.id: AlertWSInternal(
            id=instance.id, is_watched=instance.is_watched
        )
        for instance in instances
    }
    responses: ResponseMulti[AlertPublic] = ResponseMulti(
        result=instances, count=count
    )

    with suppress(ConnectionClosed):
        await websocket.send_json(json.loads(responses.json()))

    # RUN THE INF LOOP FOR TRACKING NEW ALERTS IN THE DATABASE
    while True:
        await asyncio.sleep(settings.alerts.ws_fetching_periodicity_sec)

        async with atomic(session):
            roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
                user.id,
                applet_id,
                [Role.OWNER],
            )
            if not roles:
                raise AlertViewAccessDenied

            # Get all alert for specific applet
            instances = await AlertCRUD(session).get_by_applet_id(applet_id)
            count = await AlertCRUD(session).get_by_applet_id_count(applet_id)

        for instance in instances:
            if instance.id not in last_sent_alerts.keys():
                response: Response[AlertPublic] = Response(result=instance)
                last_sent_alerts[instance.id] = AlertWSInternal(
                    id=instance.id, is_watched=instance.is_watched
                )
                try:
                    await websocket.send_json(json.loads(response.json()))
                except ConnectionClosed:
                    break

                continue

            if instance.is_watched != last_sent_alerts[instance.id].is_watched:
                last_sent_alerts[instance.id].is_watched = instance.is_watched

                response = Response(result=instance)

                try:
                    await websocket.send_json(json.loads(response.json()))
                except ConnectionClosed:
                    break
