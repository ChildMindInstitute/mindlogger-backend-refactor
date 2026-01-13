from asyncpg import InvalidPasswordError
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic_core._pydantic_core import PydanticSerializationUnexpectedValue
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from apps.shared.domain import ErrorResponse, ErrorResponseMulti
from apps.shared.exception import BaseError
from infrastructure.logger import logger


def custom_base_errors_handler(_: Request, error: BaseError) -> JSONResponse:
    """This function is called if the BaseError was raised."""

    logger.error(error.error, exc_info=error)

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


def python_base_error_handler(_: Request, error: Exception) -> JSONResponse:
    """This function is called if an Exception was raised."""

    error_message = str(error)
    response = ErrorResponseMulti(result=[ErrorResponse(message=f"Unhandled error: {error_message}")])

    logger.error(error_message, exc_info=error)

    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def pydantic_request_validation_errors_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    """This function is called if the Pydantic validation error was raised when a request is validated."""
    errors = []
    this_logger = logger.bind(
        error_location={"file": error.endpoint_file, "line": error.endpoint_line, "function": error.endpoint_function}
    )
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


def pydantic_serialization_validation_errors_handler(
    _: Request, error: PydanticSerializationUnexpectedValue
) -> JSONResponse:
    """
    This function is called if the Pydantic serialization validation error was raised when a response is serialized.
    """
    logger.error(str(error), exc_info=error)
    response = ErrorResponseMulti(result=[ErrorResponse(message="Internal server error")])

    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def sqlalchemy_database_error_handler(
    _: Request, error: TimeoutError | InvalidPasswordError | ConnectionRefusedError
) -> JSONResponse:
    """This function is called if the SQLAlchemy database error was raised."""
    logger.error(str(error), exc_info=error)
    response = ErrorResponseMulti(result=[ErrorResponse(message="Internal server error")])

    return JSONResponse(
        content=jsonable_encoder(response.model_dump(by_alias=True)),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
