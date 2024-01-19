from infrastructure.database import session_manager


async def get_session():
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        yield session


def pass_session(method):
    async def wrap_(*args, **kwargs):
        session_maker = session_manager.get_session()
        async with session_maker() as session:
            try:
                await method(*args, **kwargs, session=session)
            except Exception as e:
                print(e)

    return wrap_
