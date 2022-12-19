from fastapi.routing import APIRouter

from apps.invitations.api import send_invitation

router = APIRouter(prefix="/invitations", tags=["Invitations"])

router.post("/invite")(send_invitation)
