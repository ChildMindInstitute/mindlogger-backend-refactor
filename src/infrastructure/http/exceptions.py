import traceback

from asyncpg import InvalidPasswordError
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from apps.shared.domain import ErrorResponse, ErrorResponseMulti
from apps.shared.exception import BaseError
from config import settings
from infrastructure.logger import logger


def custom_base_errors_handler(_: Request, error: BaseError) -> JSONResponse:
    """This function is called if the BaseError was raised."""
    # TODO Some unit tests check for error messages.  Might be bad?  If the erroring endpoint doesn't log anything
    # TODO then there is nothing in the log.  Logging here ensures errors actually get logged.
    if settings.env != "testing":
        logger.warning(error.error, exc_info=error)

    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=error.error,
                type=error.type,
                path=getattr(error, "path", []),
            )
        ]
    )

    return JSONResponse(
        response.dict(by_alias=True),
        status_code=error.status_code,
    )


def python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """This function is called if the Exception was raised."""

    error_message = "".join(traceback.format_tb(error.__traceback__))
    response = ErrorResponseMulti(result=[ErrorResponse(message=f"Unhandled error: {error_message}")])

    # NOTE: replace error with warning because application can still work
    # Also it stops sending duplicate of error to the sentry.
    # (Default logging level for sending events to the sentry is ERROR.
    # It means that each logger.error sends additional event to the sentry).
    logger.warning(error, exc_info=error)

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def pydantic_validation_errors_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""
    # TODO: remove it later. This is a fix after updating fastapi version.
    errors = []
    for err in error.errors():
        if isinstance(err, dict):
            message = err["msg"]
            path = list(err["loc"])
        else:
            message = str(err.exc)
            path = list(err.loc_tuple())
        errors.append(ErrorResponse(message=message, path=path))
    response = ErrorResponseMulti(result=errors)

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def sqlalchemy_database_error_handler(
    _: Request, error: TimeoutError | InvalidPasswordError | ConnectionRefusedError
) -> JSONResponse:
    """This function is called if the SQLAlchemy database error was raised."""
    logger.error(str(error))
    response = ErrorResponseMulti(result=[ErrorResponse(message="Internal server error")])

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
