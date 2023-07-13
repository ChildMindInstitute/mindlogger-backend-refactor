import json
from collections import defaultdict

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from config import settings


class RabbitMqQueueTest(object):
    messages: dict[str, list[aio_pika.Message]] = defaultdict(list)
    routing_key = settings.rabbitmq.default_routing_key

    def __init__(self):
        self.url = settings.rabbitmq.url
        self.connection = False

    async def connect(self):
        self.connection = True
        return

    async def close(self):
        self.connection = False
        return

    async def publish(self, routing_key: str | None = None, *, data):
        assert self.connection, "Connection is closed"

        message = aio_pika.Message(json.dumps(data, default=str).encode())
        self.messages[routing_key or self.routing_key].append(message)

    async def consume(
        self, queue_name: str | None = None, *, callback, async_parallel=5
    ):
        assert self.connection, "Connection is closed"

        while len(self.messages[queue_name or self.routing_key]) != 0:
            await callback(
                type(
                    "AbstractIncomingMessage",
                    (object,),
                    {
                        "body": self.messages[
                            queue_name or self.routing_key
                        ].pop(0)
                    },
                )
            )


class RabbitMqQueue:
    routing_key = settings.rabbitmq.default_routing_key

    def __new__(cls, *args, **kwargs):
        if settings.env == "testing":
            return RabbitMqQueueTest()
        return super().__new__(cls)

    def __init__(self):
        self.url = settings.rabbitmq.url
        self.connection: AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractRobustChannel | None = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(url=self.url)
        self.channel = await self.connection.channel()

    async def close(self):
        await self.connection.close()

    async def publish(self, routing_key: str | None = None, *, data):
        message = aio_pika.Message(json.dumps(data, default=str).encode())

        assert self.channel

        await self.channel.default_exchange.publish(
            message=message, routing_key=routing_key or self.routing_key
        )

    async def consume(
        self, queue_name: str | None = None, *, callback, async_parallel=5
    ):
        assert self.channel

        await self.channel.set_qos(prefetch_count=async_parallel)
        queue = await self.channel.declare_queue(
            queue_name or self.routing_key, auto_delete=True
        )
        await queue.consume(callback)
