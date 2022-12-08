from fastapi.security import OAuth2PasswordBearer

import registry
from infrastructure.app import create_app

app = create_app(
    registry.routers,
    registry.middlewares
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
