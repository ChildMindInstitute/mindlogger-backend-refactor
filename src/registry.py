import apps.authentication.router as auth
import apps.healthcheck.router as healthcheck
from infrastructure import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
)

middlewares = (middlewares_.ErrorsHandlingMiddleware,)
