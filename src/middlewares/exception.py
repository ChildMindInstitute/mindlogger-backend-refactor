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
    ErrorResponseMessage,
    ErrorResponseMulti,
)
from apps.shared.errors import BaseError


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
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
                message=ErrorResponseMessage(en=error._message.capitalize()),
                type_=error._type,
            )
        ]
    )

    return JSONResponse(
        response.dict(by_alias=True),
        status_code=error._status_code,
    )


def _python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """This function is called if the Exception was raised."""

    response = ErrorResponseMulti(
        result=[
            ErrorResponse(
                message=ErrorResponseMessage(en=f"Unhandled error: {error}")
            )
        ]
    )

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
                message=ErrorResponseMessage(en=err["msg"]),
                path=list(err["loc"]),
            )
            for err in error.errors()
        ]
    )

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
