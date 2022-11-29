from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

from apps.authentication.api.auth import router as authentication_router
from apps.healthcheck.api import router as healthcheck_router
from middlewares import ErrorsHandlingMiddleware


def create_app():
    app = FastAPI()

    # Routers include
    app.include_router(healthcheck_router)
    app.include_router(authentication_router)

    # Middlewares configuration
    app.add_middleware(ErrorsHandlingMiddleware)

    return app


app = create_app()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
