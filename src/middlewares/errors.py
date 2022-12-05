from fastapi import Request, Response, status
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from apps.authentication.errors import AuthenticationError
from apps.shared.domain import ErrorResponse
from apps.shared.errors import (
    BaseError,
    NotContentError,
    NotFoundError,
    ValidationError,
)


class ErrorsHandlingMiddleware(BaseHTTPMiddleware):
    headers = {"Content-Type": "application/json"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            response: Response = await call_next(request)
        except AuthenticationError as error:
            resp = ErrorResponse(messages=[str(error)])
            return Response(
                resp.json(),
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers=self.headers,
            )
        except ValidationError as error:
            resp = ErrorResponse(messages=[str(error)])
            return Response(
                resp.json(),
                status_code=status.HTTP_400_BAD_REQUEST,
                headers=self.headers,
            )
        except NotFoundError as error:
            resp = ErrorResponse(messages=[str(error)])
            return Response(
                resp.json(),
                status_code=status.HTTP_404_NOT_FOUND,
                headers=self.headers,
            )
        except NotContentError:
            return Response(
                None,
                status_code=status.HTTP_204_NO_CONTENT,
                headers=self.headers,
            )
        except BaseError as error:
            resp = ErrorResponse(messages=[str(error)])
            return Response(
                resp.json(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers=self.headers,
            )
        except Exception as error:
            resp = ErrorResponse(messages=[f"Unhandled error: {error}"])
            return Response(
                resp.json(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers=self.headers,
            )

        return response
