from fastapi import status
from fastapi.routing import APIRouter

from apps.healthcheck.api import liveness, readiness, statuscode

router = APIRouter(tags=["Health check"])

router.get("/readiness", status_code=status.HTTP_200_OK)(readiness)
router.get("/liveness", status_code=status.HTTP_200_OK)(liveness)
router.get("/statuscode")(statuscode)
