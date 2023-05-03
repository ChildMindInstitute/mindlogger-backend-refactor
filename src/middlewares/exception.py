import gettext
import logging
import traceback

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request

from apps.shared.domain.response.errors import (
    ErrorResponse,
    ErrorResponseMulti,
)
from apps.shared.exception import BaseError
from config import settings

logger = logging.getLogger("mindlogger_backend")
gettext.bindtextdomain(gettext.textdomain(), settings.locale_dir)


def _custom_base_errors_handler(_: Request, error: BaseError) -> JSONResponse:
    """This function is called if the BaseError was raised."""
    print("".join(traceback.format_tb(error.__traceback__)))
    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=error.error,
                type=error.type,
                path=getattr(error, "path", []),
            )
        ]
    )

    logger.error(response)

    return JSONResponse(
        response.dict(by_alias=True),
        status_code=error.status_code,
    )


def _python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """This function is called if the Exception was raised."""

    error_message = "".join(traceback.format_tb(error.__traceback__))
    response = ErrorResponseMulti(
        result=[ErrorResponse(message=f"Unhandled error: {error_message}")]
    )

    logger.error(response)
    print("".join(traceback.format_tb(error.__traceback__)))

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _pydantic_validation_errors_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""

    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=err["msg"],
                path=list(err["loc"]),
            )
            for err in error.errors()
        ]
    )

    logger.error(response)
    print("".join(traceback.format_tb(error.__traceback__)))

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
