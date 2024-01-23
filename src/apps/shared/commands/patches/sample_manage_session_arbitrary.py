from infrastructure.database import atomic


async def main(session_maker, arbitrary_session_maker, *args, **kwargs):
    async with session_maker() as session:
        async with atomic(session):
            pass

    if arbitrary_session_maker is not None:
        async with arbitrary_session_maker() as arb_session:
            async with atomic(arb_session):
                pass
