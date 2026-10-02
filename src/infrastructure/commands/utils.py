import asyncio
from functools import wraps


def coro(f):
    """Decorator to run a coroutine as a regular function for CLI commands"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper
