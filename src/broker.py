from typing import Any, Coroutine, Union

import structlog
import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker, TaskiqMessage, TaskiqMiddleware
from taskiq.formatters.json_formatter import JSONFormatter
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from config import settings
from infrastructure.logger import logger

broker: AsyncBroker = (
    AioPikaBroker(settings.rabbitmq.url)
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


if settings.env == "testing" or settings.env == "local":
    logger.info("Starting in memory broker")
    broker = InMemoryBroker().with_formatter(JSONFormatter())

middlewares = [StructlogMiddleware()]
broker.add_middlewares(*middlewares)

taskiq_fastapi.init(broker, "main:app")
