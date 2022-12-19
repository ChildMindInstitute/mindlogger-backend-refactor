from fastapi.security import OAuth2PasswordBearer

from infrastructure.app import create_app

app = create_app()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
