from fastapi.routing import APIRouter

from apps.schedule.api.schedule import (
    schedule_create,
    schedule_delete,
    schedule_get_all,
    schedule_get_by_id,
)

router = APIRouter(prefix="/applets", tags=["Applets"])

router.post("/{applet_id}/events", status_code=201)(schedule_create)
router.get("/{applet_id}/events", status_code=200)(schedule_get_all)
router.get("/{applet_id}/events/{event_id}", status_code=200)(
    schedule_get_by_id
)
router.delete("/{applet_id}/events/{event_id}", status_code=204)(
    schedule_delete
)
