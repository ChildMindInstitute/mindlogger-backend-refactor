from typing import Iterable, Type

from fastapi import FastAPI
from fastapi.routing import APIRouter
from starlette.middleware.base import BaseHTTPMiddleware

import apps.applets.router as applets
import apps.authentication.router as auth
import apps.healthcheck.router as healthcheck
import apps.invitations.router as invitations
import apps.users.router as users
import middlewares as middlewares_

# Declare your routers here
routers: Iterable[APIRouter] = (
    healthcheck.router,
    auth.router,
    applets.router,
    users.router,
    invitations.router,
)

# Declare your middlewares here
middlewares: Iterable[Type[BaseHTTPMiddleware]] = (
    middlewares_.ErrorsHandlingMiddleware,
    # TODO: Fix the transaction.commit decorator
    # NOTE: This transaction manager makes the BaseCRUD service fail
    #       Error: Can't operate on closed transaction inside context manager.
    #              Please complete the context manager
    #              before emitting further commands
    # middlewares_.DatabaseTransactionMiddleware,
)


def create_app():
    # Create base FastAPI application
    app = FastAPI()

    # Include routers
    for router in routers:
        app.include_router(router)

    # Include middlewares
    for middleware in middlewares:
        app.add_middleware(middleware)

    return app
