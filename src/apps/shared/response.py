from starlette.responses import Response


class EmptyResponse(Response):
    media_type = "application/json"
