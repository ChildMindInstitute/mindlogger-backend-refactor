from asyncpg import InvalidPasswordError
from ddtrace import tracer
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, Response

from apps.audit import AuditEvent, EventAction, http_audit_fields, log
from apps.authentication.errors import SessionTokenInvalidError
from apps.shared.domain import ErrorResponse, ErrorResponseMulti
from apps.shared.exception import BaseError
from infrastructure.logger import logger


def _set_trace_exception(exc: Exception) -> None:
    span = tracer.current_span()
    if span:
        span.set_exc_info(type(exc), exc, exc.__traceback__)


def custom_base_errors_handler(_: HTTPConnection, error: BaseError) -> JSONResponse:
    """This function is called if the BaseError was raised."""

    logger.error(error.error, exc_info=error)
    _set_trace_exception(error)

    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=error.error,
                type=error.type,
                path=getattr(error, "path", []),
            )
        ]
    )

    response_dict = response.model_dump(by_alias=True)

    # Add error_code to response if present
    if hasattr(error, "error_code") and error.error_code:
        response_dict["error_code"] = error.error_code

    # Add metadata to response if present
    if hasattr(error, "metadata") and error.metadata:
        response_dict["metadata"] = error.metadata

    return JSONResponse(
        response_dict,
        status_code=error.status_code,
    )


async def session_token_invalid_error_handler(request: HTTPConnection, error: SessionTokenInvalidError) -> JSONResponse:
    """user:session:invalid audit event on 401 from invalid session token.

    ``request`` may be a ``WebSocket`` (e.g. the `/ws/alerts` handshake) as well as an HTTP
    ``Request``, so only fields common to both connection types may be used here.
    """
    await log(
        AuditEvent(
            event_action=EventAction.USER_SESSION_INVALID,
            user_id=error.user_id,
            **http_audit_fields(request, error),
        )
    )
    return custom_base_errors_handler(request, error)


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """user:session:invalid audit event on 401 from missing session token in `Authorization` header."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        await log(
            AuditEvent(
                event_action=EventAction.USER_SESSION_INVALID,
                user_id=None,
                **http_audit_fields(request, exc),
            )
        )
    return await http_exception_handler(request, exc)


def python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """This function is called if an Exception was raised."""

    error_message = str(error)
    response = ErrorResponseMulti(result=[ErrorResponse(message=f"Unhandled error: {error_message}")])

    logger.error(error_message, exc_info=error)
    _set_trace_exception(error)

    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def pydantic_validation_errors_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""
    errors = []
    this_logger = logger.bind(
        error_location={"file": error.endpoint_file, "line": error.endpoint_line, "function": error.endpoint_function}
    )

    _set_trace_exception(error)

    for err in error.errors():
        if isinstance(err, dict):
            message = err["msg"]
            path = list(err["loc"])
            error_type = err["type"]
            loc = ".".join(map(str, list(err.get("loc", []))))
            error_input = err.get("input")
        else:
            # TODO This else might be dead
            message = str(err.exc)
            path = list(err.loc_tuple())
            error_type = ""
            error_input = ""
        errors.append(ErrorResponse(message=message, path=path))
        this_logger.warning(message, exc_info=error, extra={"field": loc, "type": error_type, "input": error_input})

    response = ErrorResponseMulti(result=errors)
    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def sqlalchemy_database_error_handler(
    _: Request, error: TimeoutError | InvalidPasswordError | ConnectionRefusedError
) -> JSONResponse:
    """This function is called if the SQLAlchemy database error was raised."""
    logger.error(str(error), exc_info=error)
    _set_trace_exception(error)

    response = ErrorResponseMulti(result=[ErrorResponse(message="Internal server error")])

    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
