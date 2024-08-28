import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker
from taskiq.formatters.json_formatter import JSONFormatter
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from config import settings

broker: AsyncBroker = (
    AioPikaBroker(settings.rabbitmq.url)
    .with_result_backend(RedisAsyncResultBackend(settings.redis.url))
    .with_formatter(JSONFormatter())
)

if settings.env == "testing":
    broker = InMemoryBroker().with_formatter(JSONFormatter())

taskiq_fastapi.init(broker, "main:app")
