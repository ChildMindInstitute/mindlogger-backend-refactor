from typing import Iterable, Type

from fastapi import FastAPI
from fastapi.routing import APIRouter

import apps.activities.router as activities
import apps.applets.router as applets
import apps.authentication.router as auth
import apps.healthcheck.router as healthcheck
import apps.invitations.router as invitations
import apps.themes.router as themes
import apps.users.router as users
import middlewares as middlewares_

# Declare your routers here
routers: Iterable[APIRouter] = (
    healthcheck.router,
    activities.router,
    auth.router,
    applets.router,
    users.router,
    themes.router,
    invitations.router,
)

# Declare your middlewares here
middlewares: Iterable[tuple[Type[middlewares_.Middleware], dict]] = (
    (middlewares_.CORSMiddleware, middlewares_.cors_options),
    (middlewares_.ErrorsHandlingMiddleware, {}),
    (middlewares_.DatabaseTransactionMiddleware, {}),
)


def create_app():
    # Create base FastAPI application
    app = FastAPI()

    # Include routers
    for router in routers:
        app.include_router(router)

    # Include middlewares
    for middleware, options in middlewares:
        app.add_middleware(middleware, **options)

    return app
