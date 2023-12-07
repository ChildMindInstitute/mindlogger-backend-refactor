from fastapi.responses import Response
from starlette import status


def readiness():
    return Response("Readiness - OK!")


def liveness():
    return Response("Liveness - OK!")


statuses = {
    code for var, code in vars(status).items() if var.startswith("HTTP_")
}
exclude = {301, 302}
supported_statuses = statuses - exclude


def statuscode(code: int = 200):
    if code not in supported_statuses:
        return Response("Wrong status code", status_code=400)
    return Response(status_code=code)
