from fastapi import FastAPI

from apps.healthcheck.api import router as healthcheck_router


def create_app():
    app = FastAPI()
    app.include_router(healthcheck_router)
    return app


app = create_app()
