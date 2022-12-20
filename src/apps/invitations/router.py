from fastapi.routing import APIRouter

from apps.invitations.api import approve_invite, send_invitation

router = APIRouter(prefix="/invitations", tags=["Invitations"])

router.post("/invite")(send_invitation)
router.get("/approve/{key}")(approve_invite)
