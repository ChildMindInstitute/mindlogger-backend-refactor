from fastapi.responses import Response


def readiness():
    return Response("Readiness - OK!")


def liveness():
    return Response("liveness - OK!")
