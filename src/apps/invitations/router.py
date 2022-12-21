from fastapi.routing import APIRouter

from apps.invitations.api import approve_invite, invitations, send_invitation

router = APIRouter(prefix="/invitations", tags=["Invitations"])

router.get("")(invitations)
router.post("/invite")(send_invitation)
router.get("/approve/{key}")(approve_invite)

# TODO: Add decline route
# router.get("/decline/{key}")(decline_invite)
