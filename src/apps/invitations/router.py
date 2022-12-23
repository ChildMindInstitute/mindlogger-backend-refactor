from fastapi.routing import APIRouter

from apps.invitations.api import (
    approve_invite,
    decline_invite,
    invitations,
    send_invitation,
)

router = APIRouter(prefix="/invitations", tags=["Invitations"])

router.get("")(invitations)
router.post("/invite")(send_invitation)
router.get("/approve/{key}")(approve_invite)
router.get("/decline/{key}")(decline_invite)
