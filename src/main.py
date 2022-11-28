from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

from apps.authentication.api.auth import router as authentication_router
from apps.healthcheck.api import router as healthcheck_router


def create_app():
    app = FastAPI()
    app.include_router(healthcheck_router)
    app.include_router(authentication_router)
    return app


app = create_app()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
