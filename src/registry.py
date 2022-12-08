import apps.healthcheck.router as healthcheck
import apps.authentication.router as auth
from infrastructure import middlewares as middlewares_

routers = (
    healthcheck.router,
    auth.router,
)

middlewares = (
    middlewares_.ErrorsHandlingMiddleware,
)
