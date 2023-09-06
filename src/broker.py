import taskiq_fastapi
from taskiq import InMemoryBroker
from taskiq_aio_pika import AioPikaBroker

from config import settings

broker = AioPikaBroker(settings.rabbitmq.url)

if settings.env == "testing":
    broker = InMemoryBroker()

taskiq_fastapi.init(broker, "main:app")
