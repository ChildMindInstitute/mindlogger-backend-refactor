from config import settings
from infrastructure.database import session_manager


async def get_session():
    session_maker = session_manager.get_session()

    if settings.env == "testing":
        # TODO for current tests implementation support session not closed,
        #   fix and remove
        yield session_maker
    else:
        async with session_maker() as session:
            yield session
