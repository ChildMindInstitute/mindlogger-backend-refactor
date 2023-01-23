from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.schedule.domain.schedule.requests import EventRequest
from apps.schedule.domain.schedule.public import PublicEvent
from apps.schedule.service.schedule import ScheduleService
from apps.shared.domain import Response, ResponseMulti
from apps.shared.errors import NoContentError
from apps.users.domain import User


async def schedule_create(
    user: User = Depends(get_current_user),
    schema: EventRequest = Body(...),
) -> Response[PublicEvent]:

    schedule = await ScheduleService().create_schedule(schema, user.id)
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_get_by_id():
    pass


async def schedule_get_all():
    pass


async def schedule_delete():
    pass
