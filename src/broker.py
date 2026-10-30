
import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker
from taskiq.formatters.json_formatter import JSONFormatter
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from config import settings
from infrastructure.logger import logger
from middlewares.taskiq.datadog import DatadogTaskiqMiddleware
from middlewares.taskiq.errorlogger import ErrorLoggerMiddleware
from middlewares.taskiq.structlog import StructlogMiddleware

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

if settings.env == "testing" or settings.env == "local":
    logger.info("Starting in memory broker")
    broker = InMemoryBroker().with_formatter(JSONFormatter())

middlewares = [StructlogMiddleware(), ErrorLoggerMiddleware(), DatadogTaskiqMiddleware()]
broker.add_middlewares(*middlewares)

taskiq_fastapi.init(broker, "main:app")
