from typing import Any, Coroutine, Union

import structlog
import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker, TaskiqMessage, TaskiqMiddleware, TaskiqResult
from taskiq.formatters.json_formatter import JSONFormatter
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from config import settings
from infrastructure.logger import logger

broker: AsyncBroker = (
    AioPikaBroker(
        settings.rabbitmq.url,
        exchange_name="curious",
        queue_name="curious",
        declare_exchange_kwargs={"durable": True},
        declare_queues_kwargs={"durable": True},
    )
    .with_result_backend(RedisAsyncResultBackend(settings.redis.url))
    .with_formatter(JSONFormatter())
)


class StructlogMiddleware(TaskiqMiddleware):
    def pre_execute(
        self,
        message: TaskiqMessage,
    ) -> "Union[TaskiqMessage, Coroutine[Any, Any, TaskiqMessage]]":
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(taskiq_task_id=message.task_id, taskiq_task_name=message.task_name)

        return message


class ErrorLoggerMiddleware(TaskiqMiddleware):
    """Custom error logging middleware so Datadog receives errors"""

    async def on_error(self, message: TaskiqMessage, result: TaskiqResult[Any], exception: BaseException) -> None:
        logger.error(f"Task {message.task_name} failed! ", exc_info=exception)


if settings.env == "testing" or settings.env == "local":
    logger.info("Starting in memory broker")
    broker = InMemoryBroker().with_formatter(JSONFormatter())

middlewares = [StructlogMiddleware(), ErrorLoggerMiddleware()]
broker.add_middlewares(*middlewares)

taskiq_fastapi.init(broker, "main:app")
