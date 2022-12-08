from fastapi import FastAPI


def create_app(routers=None, middlewares=None):
    if not routers:
        routers = []
    if not middlewares:
        middlewares = []
    app = FastAPI()

    # Routers include
    for router in routers:
        app.include_router(router)

    # Middlewares configuration
    for middleware in middlewares:
        app.add_middleware(middleware)
    return app
