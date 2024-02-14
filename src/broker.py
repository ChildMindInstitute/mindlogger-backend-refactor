import taskiq_fastapi
from taskiq import InMemoryBroker
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from config import settings

broker = AioPikaBroker(settings.rabbitmq.url).with_result_backend(RedisAsyncResultBackend(settings.redis.url))

if settings.env == "testing":
    broker = InMemoryBroker()

taskiq_fastapi.init(broker, "main:app")
