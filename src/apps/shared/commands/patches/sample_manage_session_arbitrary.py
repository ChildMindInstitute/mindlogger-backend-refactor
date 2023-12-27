from infrastructure.database import atomic


async def main(session_maker, arbitrary_session_maker, *args, **kwargs):
    try:
        async with session_maker() as session:
            async with atomic(session):
                pass

    finally:
        await session_maker.remove()

    if arbitrary_session_maker is not None:
        try:
            async with arbitrary_session_maker() as arb_session:
                async with atomic(arb_session):
                    pass
        finally:
            await arbitrary_session_maker.remove()
