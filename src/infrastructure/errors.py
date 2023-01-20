from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request

from apps.shared.domain.response.errors import (
    ErrorResponse,
    ErrorResponseMessage,
    ErrorResponseMulti,
)
from apps.shared.errors import BaseError


async def custom_base_errors_handler(
    _: Request, error: BaseError
) -> JSONResponse:
    """This function is called if the BaseError was raised."""

    response = ErrorResponseMulti(
        results=[
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


async def python_base_error_handler(
    _: Request, error: Exception
) -> JSONResponse:
    """This function is called if the Exception was raised."""

    response = ErrorResponseMulti(
        results=[
            ErrorResponse(
                message=ErrorResponseMessage(en=f"Unhandled error: {error}")
            )
        ]
    )

    return JSONResponse(
        content=jsonable_encoder(response.dict(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def pydantic_validation_errors_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised."""

    response = ErrorResponseMulti(
        results=[
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
