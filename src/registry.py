import apps.applets.router as applets
import apps.authentication.router as auth
import apps.file.router as file
import apps.healthcheck.router as healthcheck
import apps.items.router as items
import apps.users.router as users
import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
    applets.router,
    users.router,
    file.router,
    items.router,
)

middlewares = (middlewares_.ErrorsHandlingMiddleware,)
