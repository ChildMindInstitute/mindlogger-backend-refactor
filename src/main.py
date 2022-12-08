from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

from apps.authentication.router import router as authentication_router
from apps.file.router import router as file_router
from apps.healthcheck.router import router as healthcheck_router
from middlewares import ErrorsHandlingMiddleware


def create_app():
    app = FastAPI()

    # Routers include
    app.include_router(healthcheck_router)
    app.include_router(authentication_router)
    app.include_router(file_router)

    # Middlewares configuration
    app.add_middleware(ErrorsHandlingMiddleware)

    return app


app = create_app()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
