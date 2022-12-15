import apps.authentication.router as auth
import apps.file.router as file
import apps.healthcheck.router as healthcheck
import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
    file.router,
)

middlewares = (middlewares_.ErrorsHandlingMiddleware,)
