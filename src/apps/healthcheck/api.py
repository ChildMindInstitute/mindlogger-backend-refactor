from fastapi import status
from fastapi.responses import Response
from fastapi.routing import APIRouter

router = APIRouter(tags=["Health check"])


@router.get("/readiness", status_code=status.HTTP_200_OK)
def readiness():
    return Response("Readiness - OK!")


@router.get("/liveness", status_code=status.HTTP_200_OK)
def liveness():
    return Response("liveness - OK!")
