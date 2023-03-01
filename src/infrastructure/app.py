from typing import Iterable, Type

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRouter

import apps.activities.router as activities
import apps.answers.router as answers
import apps.applets.router as applets
import apps.authentication.router as auth
import apps.folders.router as folders
import apps.healthcheck.router as healthcheck
import apps.invitations.router as invitations
import apps.logs.router as logs
import apps.schedule.router as schedule
import apps.themes.router as themes
import apps.transfer_ownership.router as transfer_ownership
import apps.users.router as users
import apps.workspaces.router as workspaces
import middlewares as middlewares_
from apps.shared.errors import BaseError
from config import settings
from infrastructure.errors import (
    custom_base_errors_handler,
    pydantic_validation_errors_handler,
    python_base_error_handler,
)

# Declare your routers here
routers: Iterable[APIRouter] = (
    healthcheck.router,
    activities.router,
    auth.router,
    applets.router,
    users.router,
    themes.router,
    invitations.router,
    logs.router,
    schedule.router,
    folders.router,
    answers.router,
    workspaces.router,
    transfer_ownership.router,
)

# Declare your middlewares here
middlewares: Iterable[tuple[Type[middlewares_.Middleware], dict]] = (
    (middlewares_.CORSMiddleware, middlewares_.cors_options),
    (middlewares_.DatabaseTransactionMiddleware, {}),
)


def create_app():
    # Create base FastAPI application
    app = FastAPI(
        description=f"Commit id: <b>{settings.commit_id}"
        f"</b><br>Version: <b>{settings.version}</b>"
    )
    if settings.sentry.dsn:
        sentry_sdk.init(dsn=settings.sentry.dsn, traces_sample_rate=1.0)

    # Include routers
    for router in routers:
        app.include_router(router)

    # Include middlewares
    for middleware, options in middlewares:
        app.add_middleware(middleware, **options)

    # Error handling
    app.exception_handler(RequestValidationError)(
        pydantic_validation_errors_handler
    )
    app.exception_handler(BaseError)(custom_base_errors_handler)
    app.exception_handler(Exception)(python_base_error_handler)

    return app
