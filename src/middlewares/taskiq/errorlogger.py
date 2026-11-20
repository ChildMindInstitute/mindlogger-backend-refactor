from typing import Any

from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from infrastructure.logger import logger


class ErrorLoggerMiddleware(TaskiqMiddleware):
    """Custom error logging middleware so Datadog receives errors"""

    async def on_error(self, message: TaskiqMessage, result: TaskiqResult[Any], exception: BaseException) -> None:
        logger.warning(f"Task {message.task_name} failed! ", exc_info=exception)
