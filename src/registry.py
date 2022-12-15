import apps.applets.router as applets
import apps.authentication.router as auth
import apps.healthcheck.router as healthcheck
import apps.users.router as users
import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
    applets.router,
    users.router,
)

middlewares = (middlewares_.ErrorsHandlingMiddleware,)
