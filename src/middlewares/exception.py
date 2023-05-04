import gettext
import logging
import os
import traceback

from fastapi import Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette import status
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request

from apps.shared.domain.response.errors import (
    ErrorResponse,
    ErrorResponseMulti,
)
from apps.shared.exception import BaseError
from config import settings
from infrastructure.http import get_language

logger = logging.getLogger("mindlogger_backend")
gettext.bindtextdomain(gettext.textdomain(), settings.locale_dir)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        os.environ["LANG"] = get_language(request)
        try:
            return await call_next(request)
        except BaseError as e:
            return _custom_base_errors_handler(request, e)
        except ValidationError as e:
            return _pydantic_validation_errors_handler(request, e)
        except Exception as e:
            return _python_base_error_handler(request, e)


def _custom_base_errors_handler(_: Request, error: BaseError) -> JSONResponse:
    """This function is called if the BaseError was raised."""
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

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _pydantic_validation_errors_handler(
    _: Request, error: ValidationError
) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""

    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=err["msg"],
                path=list(err["loc"]),
                type=err["type"],
            )
            for err in error.errors()
        ]
    )

    logger.error(response)

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
