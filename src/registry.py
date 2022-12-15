import apps.authentication.router as auth
import apps.healthcheck.router as healthcheck
import apps.file.router as file
import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
    file.router,
)

middlewares = (middlewares_.ErrorsHandlingMiddleware,)
